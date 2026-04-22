# -*- coding: utf-8 -*-
import os
import json
from voice_feature_extractor import VoiceFeatureExtractor
from content_feature_extractor import ContentFeatureExtractor
import librosa

def get_audio_duration(audio_path):
    try:
        y, sr = librosa.load(audio_path, sr=16000)
        duration = len(y) / sr
        return duration
    except Exception as e:
        print(f'Error getting duration for {audio_path}: {e}')
        return 0

def process_audio_file(audio_path, voice_extractor, content_extractor):
    filename = os.path.basename(audio_path)
    file_id = filename.replace(' ', '_').replace('(', '').replace(')', '').replace('.', '_')
    
    print(f'Processing: {filename}')
    
    # Metadata
    metadata = {
        'filename': filename,
        'duration_seconds': get_audio_duration(audio_path),
        'file_size_bytes': os.path.getsize(audio_path),
        'file_path': audio_path
    }
    
    # Voice features
    try:
        voice_features = voice_extractor.extract_acoustic_features(audio_path)
        speaker_embedding = voice_extractor.extract_speaker_embeddings(audio_path)
    except Exception as e:
        print(f'Error extracting voice features: {e}')
        voice_features = {}
        speaker_embedding = []
    
    # Content features
    try:
        transcription = content_extractor.transcribe_audio(audio_path)
        tfidf_keywords = content_extractor.extract_tfidf_keywords(transcription)
        semantic_embedding = content_extractor.extract_semantic_embeddings(transcription)
    except Exception as e:
        print(f'Error extracting content features: {e}')
        transcription = ''
        tfidf_keywords = {}
        semantic_embedding = []
    
    # Combine all
    audio_data = {
        '_id': file_id,
        'metadata': metadata,
        'voice_features': {
            'acoustic_features': voice_features,
            'speaker_embedding': speaker_embedding
        },
        'content_features': {
            'transcription': transcription,
            'tfidf_keywords': tfidf_keywords,
            'semantic_embedding': semantic_embedding
        }
    }
    
    return audio_data

def main():
    # Khởi tạo extractors
    print('Initializing extractors...')
    voice_extractor = VoiceFeatureExtractor()
    content_extractor = ContentFeatureExtractor()
    
    # Thư mục chứa audio
    audio_dir = 'Am_Thanh_Data/ĐỐI NHÂN XỬ THẾ'
    
    # Lấy danh sách tệp audio
    audio_files = []
    for file in os.listdir(audio_dir):
        if file.endswith(('.mp3', '.wav', '.flac')):
            audio_files.append(os.path.join(audio_dir, file))
    
    print(f'Found {len(audio_files)} audio files')
    
    # Xử lý từng tệp
    all_data = []
    for audio_path in audio_files:
        try:
            data = process_audio_file(audio_path, voice_extractor, content_extractor)
            all_data.append(data)
        except Exception as e:
            print(f'Error processing {audio_path}: {e}')
    
    # Lưu kết quả
    output_file = 'audio_features_database.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f'Processed {len(all_data)} files. Results saved to {output_file}')
    
    # In thống kê
    print('\nStatistics:')
    print(f'Total files processed: {len(all_data)}')
    total_duration = sum(item['metadata']['duration_seconds'] for item in all_data)
    print(f'Total duration: {total_duration:.2f} seconds ({total_duration/3600:.2f} hours)')

if __name__ == '__main__':
    main()
