# data_aggregator.py
import pandas as pd

def find_continuation_index_slice(list1, list2):
    """
     Finds the index in list2 where items no longer overlap 
     with the end of list1.
     Compares end-slice of list1 with start-slice of list2.
    """
    len1 = len(list1)
    len2 = len(list2)
    # The maximum number of items that *could* possibly overlap
    max_possible_overlap = min(len1, len2)

    # Check from the LARGEST possible overlap size down to 1
    for overlap_size in range(max_possible_overlap, 0, -1):
        # Does the end of list1 match the start of list2 for this size?
        if list1[-overlap_size:] == list2[:overlap_size]:
             # Yes! Found the largest overlap. 
             # The index to start from is the size of that overlap.
            return overlap_size 
            
    # If the loop finishes, no overlap was found at all
    return 0

def aggregate_receipt_data(all_frames_data):
    """
    Aggregates data extracted from all frames.
    all_frames_data: A list of lists, where each inner list contains
                     item dicts from one frame.
                     e.g., [[frame1_item1, frame1_item2], [frame2_item1]]
    """
    flat_list_of_items = []
    
    for index, frame_items in enumerate(all_frames_data):
        idx = 0
        # if index != 0:
        #     idx = find_continuation_index_slice(all_frames_data[index-1], frame_items)
        flat_list_of_items.extend(frame_items[idx:])

    if not flat_list_of_items:
        return pd.DataFrame(columns=['Item Name', 'Item Size', 'Cost Per Item ($)'])

    df = pd.DataFrame(flat_list_of_items)

    # Normalize item names
    df['normalized_item_name'] = df['item_name'].astype(str).str.upper().str.strip()

    # Handle quantity: if 'item_size' is None or not a number, assume 1
    def parse_size(q):
        if pd.isna(q) or q == '':
            return 1
        try:
            val = int(q)
            return val if val > 0 else 1
        except (ValueError, TypeError):
            return 1 # If it's not a number, assume 1

    df['item_size'] = df['item_size'].apply(parse_size)
    df['price_per_unit'] = pd.to_numeric(df['price_per_unit'], errors='coerce')

    # # Drop rows where essential data might be missing after coercion
    # df.dropna(subset=['normalized_item_name', 'price_per_unit'], inplace=True)
    if df.empty:
        return pd.DataFrame(columns=['Item Name', 'Item Size', 'Cost Per Item ($)'])
    
    # Extract date and back fill it.
    is_item = lambda item: None if any(i.isalpha() for i in item) else item
    df['Date'] = df["normalized_item_name"].apply(is_item)
    df['Date'] = df['Date'].bfill()
    # df = df[df["normalized_item_name"].apply(is_item).apply(lambda x: not bool(x))]

     # Aggregate data
    id_cols = df.columns.tolist()
    change_flags = (df[id_cols] != df[id_cols].shift(1)).any(axis=1)
    group_ids = change_flags.cumsum()

    df = df.groupby(group_ids).agg(
        # For each original column, take the first value in the group
        **{col: (col, 'first') for col in id_cols},
        # Create the 'Quantity' column by counting the items in each group
        Quantity=(id_cols[0], 'size')
    ).reset_index(drop=True)

    # Final columns as per user request
    final_df = df[["Date", "Quantity", "normalized_item_name", "price_per_unit"]]
    final_df.columns = ["Date", "Quantity", 'Item Name', 'Cost Per Item ($)'] # Item Size
    
    # # Sort for consistency (optional)
    # df = df.sort_values(by=['Item Name']).reset_index(drop=True)
    
    print(f"Aggregated data:\n{final_df.to_string()}")
    return final_df

if __name__ == "__main__":
    df = pd.read_csv("temp_files/tmpvxllhhum.csv")
    is_item = lambda item: None if any(i.isalpha() for i in item) else item
    df['Date'] = df["Item Name"].apply(is_item)
    df['Date'] = df['Date'].bfill()
    print(df)
