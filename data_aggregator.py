# data_aggregator.py
import pandas as pd

def aggregate_receipt_data(all_frames_data):
    """
    Aggregates data extracted from all frames.
    all_frames_data: A list of lists, where each inner list contains
                     item dicts from one frame.
                     e.g., [[frame1_item1, frame1_item2], [frame2_item1]]
    """
    flat_list_of_items = [item for frame_items in all_frames_data for item in frame_items]

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

    # Drop rows where essential data might be missing after coercion
    df.dropna(subset=['normalized_item_name', 'price_per_unit'], inplace=True)
    if df.empty:
        return pd.DataFrame(columns=['Item Name', 'Item Size', 'Cost Per Item ($)'])


    # Final columns as per user request
    final_df = df[["normalized_item_name", "item_size", "price_per_unit"]]
    final_df.columns = ['Item Name', 'Item Size', 'Cost Per Item ($)']
    
    # # Sort for consistency (optional)
    # df = df.sort_values(by=['Item Name']).reset_index(drop=True)
    
    # Aggregate data
    id_cols = final_df.columns.tolist()
    change_flags = (final_df[id_cols] != final_df[id_cols].shift(1)).any(axis=1)
    group_ids = change_flags.cumsum()

    final_df = final_df.groupby(group_ids).agg(
        # For each original column, take the first value in the group
        **{col: (col, 'first') for col in id_cols},
        # Create the 'Quantity' column by counting the items in each group
        Quantity=(id_cols[0], 'size')
    ).reset_index(drop=True)

    print(f"Aggregated data:\n{final_df.to_string()}")
    return final_df

if __name__ == "__main__":
    ...


    