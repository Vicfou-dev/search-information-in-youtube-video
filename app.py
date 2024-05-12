
from bs4 import BeautifulSoup
import re
from youtube_transcript_api import YouTubeTranscriptApi
from flask import Flask, jsonify
from supabase_py import create_client, Client
from urllib.parse import urlparse, parse_qs

supabase_url = "https://your-supabase-url.supabase.co"
supabase_anon_key = "your-anon-key"
supabase = create_client(supabase_url, supabase_anon_key)

app = Flask(__name__)

def extract_youtube_urls(filename):
    with open(filename, 'r') as f:
        contents = f.read()

    soup = BeautifulSoup(contents, 'html.parser')
    links = soup.find_all('a')

    youtube_links = [link.get('href') for link in links if 'youtube.com/watch' in link.get('href')]
    youtube_ids = [parse_qs(urlparse(link.get('href')).query).get('v')[0] for link in youtube_links]
    return [{'link': link, 'id': id} for link, id in zip(youtube_links, youtube_ids)]

def get_all_video_ids(supabase: Client):
    result = supabase.table('transcripts').select('video_id').execute()
    if result['data']:
        return [item['video_id'] for item in result['data']]
    else:
        return []
    
def get_transcripts(video_ids):
    transcripts = {}
    video_id_with_transcript = get_all_video_ids()
    for video_id in video_ids:
        if video_id in video_id_with_transcript:
            continue
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_generated_transcript(['fr', 'en'])
            transcripts[video_id] = transcript.fetch()
        except YouTubeTranscriptApi.CouldNotRetrieveTranscript:
            print(f"Could not retrieve transcript for video: {video_id}")
    return transcripts

def store_transcripts_in_supabase(supabase: Client, transcripts):
    for video_id, transcript in transcripts.items():
        for entry in transcript:
            data = {
                'video_id': video_id,
                'start': entry['start'],
                'duration': entry['duration'],
                'text': entry['text']
            }
            supabase.table('transcripts').insert(data)

@app.route('/')
def home():
    return "Hello, World!"

@app.route('/api/test')
def api():
    youtube_links = extract_youtube_urls('examples/favoris.html')
    transcripts = get_transcripts(youtube_links)
    store_transcripts_in_supabase(supabase, transcripts)
    return jsonify(youtube_links)


if __name__ == '__main__':
    app.run(debug=True)