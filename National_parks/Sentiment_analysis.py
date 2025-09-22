
import pandas as pd
import os
from textblob import TextBlob

# Function to classify emotion
def classify_emotion(review, stars):
    if pd.isna(review) or review.strip() == '':
        # Check the stars column for classification
        if stars > 3:
            return 'Positive'
        elif stars == 3:
            return 'Neutral'
        else:
            return 'Negative'
    
    analysis = TextBlob(review)
    if analysis.sentiment.polarity > 0:
        return 'Positive'
    elif analysis.sentiment.polarity < 0:
        return 'Negative'   
    else:
        return 'Neutral'

# Function to process all CSV files in a folder
def process_reviews(input_folder, output_folder):
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Iterate through all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith('.csv'):
            file_path = os.path.join(input_folder, filename)
            df = pd.read_csv(file_path)

            # Check if 'Review' and 'Stars' columns exist
            if 'text' in df.columns and 'stars' in df.columns:
                # Apply emotion classification
                df['Emotion'] = df.apply(lambda row: classify_emotion(row['text'], row['stars']), axis=1)

                # Save the updated DataFrame to the output folder
                output_file_path = os.path.join(output_folder, filename)
                df.to_csv(output_file_path, index=False)
                print(f'Processed and saved: {output_file_path}')
            else:
                print(f"'Review' or 'Stars' column not found in {filename}")

# Specify input and output folders
input_folder = r'C:\Personal\Masters\Masters_work\Study\Y1_S1\IT_code_fair\Data_science_challenge\National_parks\Raw_Reviews'  # Change this to your input folder path
output_folder = r'C:\Personal\Masters\Masters_work\Study\Y1_S1\IT_code_fair\Data_science_challenge\National_parks\Sentiment_analysis'  # Change this to your output folder path

# Run the processing function
process_reviews(input_folder, output_folder)


# df = pd.read_csv(r'C:\Personal\Masters\Masters_work\Study\Y1_S1\IT_code_fair\Data_science_challenge\National_parks\Sentiment_analysis\Charles_Darwin_University_Park_dataset_Google-Maps-Reviews-Scraper_2025-09-21_15-21-49-583.csv')
# df_slice = df[['text', 'stars', 'Emotion']]
# # %%
