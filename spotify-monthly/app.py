import os
from flask import Flask, request, jsonify, url_for, session, redirect, render_template
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from datetime import datetime

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")
app.config['SESSION_COOKIE_NAME'] = 'Session Cookie'
TOKEN_INFO = "token_info"

# Landing page before logging in
@app.route('/')
def index():
    return render_template('index.html')

# Creates the login/authentication page
@app.route('/login')
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# This is the page the site takes you to after authentication
@app.route('/redirect')
def redirectPage():
    sp_oauth = create_spotify_oauth()
    session.clear()

    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session[TOKEN_INFO] = token_info
    return redirect(url_for("getTracks", _external=True))

# Retrieve user's current top 15 songs for the month
@app.route('/getTracks')
def getTracks():
    try:
        token_info = get_token()
        sp = spotipy.Spotify(auth=token_info['access_token'])
        song_objects = sp.current_user_top_tracks(time_range='short_term', limit=15, offset=0)['items']
        songs_data = clean_song_data(song_objects)
        return render_template('top_tracks.html', songs=songs_data)
    except Exception as e:
        app.logger.error(f"An error occurred: {str(e)}")
        return redirect(url_for('login'))

# Create playlist for input song data
@app.route('/createPlaylist')
def create_playlist():
    try:
        token_info = get_token()
        sp = spotipy.Spotify(auth=token_info['access_token'])
        song_objects = sp.current_user_top_tracks(time_range='short_term', limit=15, offset=0)['items']

        track_ids = [track['id'] for track in song_objects]
        username = sp.me()['id']
        month_year = datetime.today().strftime('%B %Y')
        playlist_name = f"My Top 15 Songs - {month_year}"
        playlist_description = "made with {plaholder for site name}.com"
        playlist = sp.user_playlist_create(username, playlist_name, description=playlist_description)

        sp.playlist_add_items(playlist['id'], track_ids)

        return "Your playlist has been created successfully!"
    except Exception as e:
        app.logger.error(f"Error creating playlist: {str(e)}")
        return "Failed to create playlist. Please try again later.", 500

# Extract just the necessary data needed from the song JSON data
def clean_song_data(json_data):
    new_json = []
    
    for song in json_data:
        song_data = {}

        song_data['name'] = song['name']
        song_data['artist'] = song['artists'][0]['name']
        song_data['album_name'] = song['album']['name']
        song_data['cover_art'] = song['album']['images'][1]['url']
        song_data['audio_sample_url'] = song['preview_url']

        new_json.append(song_data)

    return new_json

# Check if authorization token is available, refresh as needed
def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        raise "exception"
    now = int(time.time())
    is_expired = (token_info['expires_at'] - now) < 60
    if (is_expired):
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    return token_info

# Create spotify authentication object
def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=url_for("redirectPage", _external=True),
        scope="user-top-read playlist-modify-public"
    )

# Retrieve the users' top 10 played artists
@app.route('/getArtists')
def getArtists():
    try:
        token_info = get_token()
        sp = spotipy.Spotify(auth=token_info['access_token'])

        # Retrieve top artists
        artist_objects = sp.current_user_top_artists(time_range='short_term', limit=15, offset=0)['items']
        artists_data = clean_artist_data(artist_objects)

        # Calculate total minutes listened for each artist
        # recently_played = sp.current_user_recently_played(limit=50)
        # artist_play_time = calculate_artist_play_time(recently_played)

        # Add play time data to artists
        # for artist in artists_data:
        #    artist_id = artist['id']
        #    artist['minutes_listened'] = artist_play_time.get(artist_id, 0)

        return render_template('top_artists.html', artists=artists_data)
    except Exception as e:
        app.logger.error(f"An error occurred: {str(e)}")
        return redirect(url_for('login'))


# Cleaning up the artist JSON data
def clean_artist_data(json_data):
    new_json = []

    for artist in json_data:
        artist_data = {
            'id': artist['id'],
            'name': artist['name'],
            'image_url': artist['images'][0]['url'] if artist['images'] else None
        }
        new_json.append(artist_data)

    return new_json

# Getting the total listening time per artist over the 4 weeks
def calculate_artist_play_time(recently_played):
    artist_play_time = {}

    for item in recently_played['items']:
        track = item['track']
        duration_ms = track['duration_ms']
        duration_minutes = duration_ms / (1000 * 60)

        for artist in track['artists']:
            artist_id = artist['id']
            if artist_id in artist_play_time:
                artist_play_time[artist_id] += duration_minutes
            else:
                artist_play_time[artist_id] = duration_minutes
    return artist_play_time


def get_spotify_user_stats():
    # new page for a user (create some sort of spotify dashboard)
    # pages: top artists, top songs, listening minutes (songs, genres, etc.)
    return 0



@app.route('/logout')
def logout():
    session.clear()  # Clears the session data
    return redirect(url_for('index'))  # Redirects to the homepage

if __name__ == "__main__":
    app.run()