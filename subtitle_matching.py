import pandas as pd

# Load the CSV file
csv_file_path = './data/cleaned/all_cleaned_data.csv'
df_csv = pd.read_csv(csv_file_path, sep=';')

# Convert 'Program' to lowercase for consistency in merging
df_csv['Program'] = df_csv['Program'].str.lower()

# Convert 'Date' in df_csv to datetime and then to 'dd.mm.yyyy' format
df_csv['Date'] = pd.to_datetime(df_csv['Date'], format='%d.%m.%y').dt.strftime('%d.%m.%Y')

# Load the Excel files for Tagesschau and Tagesthemen
tagesschau_file_path = './data/Tagesschau.xlsx'
tagesthemen_file_path = './data/Tagesthemen.xlsx'

# Selecting only necessary columns
columns_to_keep = ['Datum', 'Titel 1', 'Sendedauer Sendung', 'Uhrzeit']

df_tagesschau = pd.read_excel(tagesschau_file_path, header=1, usecols=columns_to_keep)
df_tagesthemen = pd.read_excel(tagesthemen_file_path, header=1, usecols=columns_to_keep)

# Process 'Titel 1' to extract program name and convert to lowercase
df_tagesschau['Processed Title'] = df_tagesschau['Titel 1'].str.extract(r'^(Tagesschau|Tagesthemen)')[0].str.lower()
df_tagesthemen['Processed Title'] = df_tagesthemen['Titel 1'].str.extract(r'^(Tagesschau|Tagesthemen)')[0].str.lower()

# Merge with Tagesschau data
merged_tagesschau = pd.merge(df_csv, df_tagesschau, left_on=['Program', 'Date'], right_on=['Processed Title', 'Datum'])

# Merge with Tagesthemen data
merged_tagesthemen = pd.merge(df_csv, df_tagesthemen, left_on=['Program', 'Date'], right_on=['Processed Title', 'Datum'])

# Combine both merged DataFrames
combined_df = pd.concat([merged_tagesschau, merged_tagesthemen], ignore_index=True)

# Save the combined DataFrame
# combined_df.to_csv('./data/all_cleaned_data_timed.csv')

# Print the combined DataFrame
print(combined_df)

# Adjusted frame rate (assumed frame rate; change if different)
frame_rate = 25

# Function to convert seconds since midnight to HH:MM:SS:FF format
def seconds_to_hhmmssff(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    frames = int((seconds - int(seconds)) * frame_rate)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}:{frames:02d}"

# Function to convert HH:MM:SS:FF to seconds
def hhmmssff_to_seconds(time_str):
    h, m, s, f = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s + f / frame_rate

# Convert 'Uhrzeit' to HH:MM:SS:FF format assuming 'Uhrzeit' is in seconds since midnight
combined_df['EP_Start'] = combined_df['Uhrzeit'].apply(seconds_to_hhmmssff)

# Detect new episodes
combined_df['new_episode'] = (
    (combined_df['Timecode In'] < combined_df['Timecode In'].shift(1, fill_value='00:00:00:00')) |
    (combined_df['Program'] != combined_df['Program'].shift(1)) |
    (combined_df['EP_Start'] != combined_df['EP_Start'].shift(1))
)

# Initialize episode counter
combined_df['episode_counter'] = combined_df['new_episode'].cumsum()

# Loop to calculate 'current_start' and 'current_end'
episode_starts = {}  # Dictionary to store the start times for each episode

for index, row in combined_df.iterrows():
    episode_num = row['episode_counter']
    
    if row['new_episode']:
        # New episode: set the start time and store it in the dictionary
        episode_starts[episode_num] = hhmmssff_to_seconds(row['EP_Start'])
        current_start_time = episode_starts[episode_num]
    else:
        # Same episode: retrieve the start time from the dictionary
        current_start_time = episode_starts[episode_num] + hhmmssff_to_seconds(row['Timecode In']) - hhmmssff_to_seconds(combined_df.iloc[0]['Timecode In'])

    # Calculate current_start and current_end relative to the episode start time
    combined_df.at[index, 'current_start'] = current_start_time
    combined_df.at[index, 'current_end'] = current_start_time + hhmmssff_to_seconds(row['Timecode Out']) - hhmmssff_to_seconds(row['Timecode In'])

# Convert 'current_start' and 'current_end' back to HH:MM:SS:FF format for display
combined_df['current_start'] = combined_df['current_start'].apply(seconds_to_hhmmssff)
combined_df['current_end'] = combined_df['current_end'].apply(seconds_to_hhmmssff)

# Display the DataFrame
print(combined_df[['Program', 'EP_Start', 'Timecode In', 'current_start', 'current_end', 'episode_counter']])

# combined_df.to_csv('./data/all_cleaned_data_timed')

# Load the labels DataFrame
labels_df = pd.read_csv('./data/combined_pdf_data.csv', dtype={'Start Time': str})

def start_time_to_seconds(time_str):
    time_str = str(time_str).strip()
    if ':' not in time_str or time_str == 'nan':
        return 0
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        s = float(s.split('.')[0])  # Truncate the decimal part
        return int(h) * 3600 + int(m) * 60 + int(s)
    else:
        return 0

# Convert Duration to seconds (assuming format "M'SS\"")
def duration_to_seconds(duration_str):
    minutes, seconds = duration_str.split("'")
    seconds = seconds.replace('"', '')  # Remove the double-quote character
    return int(minutes) * 60 + int(seconds)

labels_df['Start Time Sec'] = labels_df['Start Time'].apply(start_time_to_seconds)
labels_df['Duration Sec'] = labels_df['Duration'].apply(duration_to_seconds)
labels_df['End Time Sec'] = labels_df['Start Time Sec'] + labels_df['Duration Sec']

print(labels_df.head())
# Assuming combined_df is already loaded and contains 'Program', 'Date', 'current_start', 'current_end'
# Convert 'current_start' and 'current_end' in combined_df to seconds
def hhmmssff_to_seconds(time_str):
    h, m, s, f = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s + f / frame_rate

combined_df['current_start_sec'] = combined_df['current_start'].apply(hhmmssff_to_seconds)
combined_df['current_end_sec'] = combined_df['current_end'].apply(hhmmssff_to_seconds)

# Round down 'current_start_sec' and round up 'current_end_sec' without the math package
combined_df['current_start_sec'] = combined_df['current_start_sec'].apply(lambda x: int(x))
combined_df['current_end_sec'] = combined_df['current_end_sec'].apply(lambda x: int(x + 0.999999))

# Print the first 5 entries of relevant columns from labels_df
print("First 5 entries from labels_df:")
print(labels_df[['Programme', 'Date', 'Start Time Sec', 'End Time Sec']].head())

# Print the first 5 entries of relevant columns from combined_df
print("\nFirst 5 entries from combined_df:")
print(combined_df[['Program', 'Date', 'current_start_sec', 'current_end_sec']].head())

# Function to append segment info from labels_df to combined_df
def append_segment_info(row):
    # Filter labels_df for matching rows
    matching_segments = labels_df[
        (labels_df['Programme'].str.lower() == row['Program'].lower()) &
        (labels_df['Date'] == row['Date']) &
        (labels_df['Start Time Sec'] <= row['current_end_sec']) &
        (labels_df['End Time Sec'] >= row['current_start_sec'])
    ]

    # Check if there are any segments with the content type "O-Ton"
    o_ton_segments = matching_segments[matching_segments['Content Type'] == 'O-Ton']

    # Prioritize "O-Ton" content type if present
    if not o_ton_segments.empty:
        # If there are multiple "O-Ton" segments, you can prioritize by another criterion, like start time
        match = o_ton_segments.iloc[0]  # Taking the first "O-Ton" segment
    elif not matching_segments.empty:
        # If there's no "O-Ton" but there are other segments, take the first one
        match = matching_segments.iloc[0]
    else:
        # If there are no matching segments
        row['matched'] = False
        return row  # Return early as there's no match

    # Set the segment information from the prioritized match
    row['Content Type'] = match['Content Type']
    row['Speaker Name'] = match['Speaker Name']
    row['Speaker Description'] = match['Speaker Description']
    row['Segment Description'] = match['Segment Description']
    row['matched'] = True

    return row

# Apply the function to combined_df
combined_df = combined_df.apply(append_segment_info, axis=1)

# Print the DataFrame to verify the results
print(combined_df.head())

# Remove duplicate rows from combined_df
unique_combined_df = combined_df.drop_duplicates()

# Save the unique rows to a CSV file
unique_combined_df.to_csv('all_cleaned_data_timed_info.csv', index=False)

# Select required columns
columns_to_keep = ['Content Type', 'Date', 'Program', 'Segment Description', 'Speaker Description', 'Speaker Name', 'Subtitle']
unique_combined_df = unique_combined_df[columns_to_keep]

# Define the introductory phrases to exclude
intro_phrases = ["heute im studio", "hier ist das erste", "diese sendung wurde", "zur tagesschau", "live- untertitelun"]

# Function to check if a row contains any of the introductory phrases
def contains_intro_phrases(segment_desc, speaker_desc, subtitle):
    segment_desc = segment_desc.lower() if isinstance(segment_desc, str) else ""
    speaker_desc = speaker_desc.lower() if isinstance(speaker_desc, str) else ""
    subtitle = subtitle.lower() if isinstance(subtitle, str) else ""
    return any(phrase in segment_desc or phrase in speaker_desc or phrase in subtitle for phrase in intro_phrases)

# First, filter out all rows with introductory phrases
filtered_df = unique_combined_df[~unique_combined_df.apply(lambda row: contains_intro_phrases(row['Segment Description'], row['Speaker Description'], row['Subtitle']), axis=1)]

# Initialize a list to hold the indices of the rows to keep
rows_to_keep = []

# Iterate through the filtered DataFrame
for i in range(len(filtered_df)):
    # Check if the current row has a 'Content Type'
    if pd.notnull(filtered_df.iloc[i]['Content Type']):
        # Include this row and up to 10 preceding rows that do not contain intro phrases
        start_index = max(0, i - 10)
        for j in range(start_index, i + 1):
            if not contains_intro_phrases(filtered_df.iloc[j]['Segment Description'], filtered_df.iloc[j]['Speaker Description'], filtered_df.iloc[j]['Subtitle']):
                rows_to_keep.append(j)
        # Include the current row as well
        rows_to_keep.append(i)

# Remove duplicate indices
rows_to_keep = list(set(rows_to_keep))

# Function to determine affiliation based on description
def determine_affiliation(description):
    if pd.isna(description) or description.strip() == "":
        return None
    description = description.lower()  # Convert to lowercase to ensure consistent matching
    if 'moderation' in description or 'korrespondent' in description:
        return 'ARD'
    elif 'fdp' in description:
        return 'FDP'
    elif 'spd' in description:
        return 'SPD'
    elif 'bundeskanzler/spd' in description:
        return 'SPD'
    elif 'freie wähler' in description:
        return 'Freie Wähler'
    elif 'afd' in description:
        return 'AFD'
    elif 'die linke' in description:
        return 'Die Linke'
    elif 'cdu' in description or 'csu' in description:
        return 'CDU/CSU'
    elif 'bündnis 90' in description or 'die grünen' in description:
        return 'Die Grünen'
    else:
        return 'Expert'

# Apply the function to create the 'affiliation' column in filtered_df
filtered_df['affiliation'] = filtered_df['Speaker Description'].apply(determine_affiliation)

# Function to extract the first two words from a name
def extract_first_two_words(name):
    if pd.isna(name):
        return ""
    parts = name.split()
    return ' '.join(parts[:2])

# Create a map of first two words of speaker name to affiliation
affiliation_map = {}
for _, row in filtered_df.iterrows():
    if not pd.isna(row['Speaker Name']) and not pd.isna(row['affiliation']):
        key = extract_first_two_words(row['Speaker Name'])
        affiliation_map[key] = row['affiliation']

# Function to determine affiliation based on the first two words of the speaker name
def determine_affiliation_from_name(name):
    key = extract_first_two_words(name)
    return affiliation_map.get(key, None)

# Assign affiliations using the map
#filtered_df['affiliation'] = filtered_df['Speaker Name'].apply(determine_affiliation_from_name)

# Sort the DataFrame by 'Date'
cleaned_df = filtered_df.iloc[rows_to_keep].reset_index(drop=True)
cleaned_df['Date'] = pd.to_datetime(cleaned_df['Date'], format='%d.%m.%Y')
cleaned_df = cleaned_df.sort_values(by='Date')

# Save the cleaned DataFrame
cleaned_df.to_csv('cleaned_data_final.csv', index=False)


# Filter the DataFrame to include only rows where the 'Speaker Name' is 'Olaf Scholz'
olaf_scholz_rows = filtered_df[filtered_df['Speaker Name'].str.contains("Olaf Scholz", na=False)]

# Selecting only the 'Speaker Name' and 'Affiliation' columns
olaf_scholz_rows_filtered = olaf_scholz_rows[['Speaker Name', 'affiliation']]

# Printing the result
print(olaf_scholz_rows_filtered)