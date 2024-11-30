import pandas as pd
from satorilib.utils.memory import Memory


def test_merge():
    # Test case 1: Empty list of DataFrames
    dfs = []
    target_column = 'Value'
    merged_df = Memory.merge(dfs, target_column)
    assert merged_df is None
    # Test case 2: Single DataFrame
    df1 = pd.DataFrame({'Value': [1, 2, 3]})
    dfs = [df1]
    target_column = 'Value'
    merged_df = Memory.merge(dfs, target_column)
    pd.testing.assert_frame_equal(merged_df, df1)
    # Test case 3: Multiple DataFrames with target column
    df2 = pd.DataFrame(
        {
            'values': [10, 15, 20, 25, 30, 35, 40, 45, 50, 55],
            'category': ['A', 'B', 'A', 'B', 'A', 'B', 'A', 'B', 'A', 'B'],
        },
        index=pd.date_range(
            start='2023-06-30 00:00:00',
            periods=10,
            freq='H',
            tz='UTC'))
    df3 = pd.DataFrame(
        {'value': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]},
        index=pd.date_range(
            start='2023-06-30 00:00:00',
            periods=10,
            freq='31T',
            tz='UTC'))
    dfs = [df2, df3]
    target_column = 'value'
    merged_df = Memory.merge(dfs, target_column)
    expected_df = pd.DataFrame(
        {
            'value': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9,],
            'values': [10, 10, 15, 15, 20, 20, 25, 25, 30, 30,],
            'category': ['A', 'A', 'B', 'B', 'A', 'A', 'B', 'B', 'A', 'A',]},
        index=[
            '2023-06-30 00:00:00+00:00',
            '2023-06-30 00:31:00+00:00',
            '2023-06-30 01:02:00+00:00',
            '2023-06-30 01:33:00+00:00',
            '2023-06-30 02:04:00+00:00',
            '2023-06-30 02:35:00+00:00',
            '2023-06-30 03:06:00+00:00',
            '2023-06-30 03:37:00+00:00',
            '2023-06-30 04:08:00+00:00',
            '2023-06-30 04:39:00+00:00',
        ])
    pd.testing.assert_frame_equal(merged_df, expected_df)
    merged_df = Memory.mergeAllTime(dfs)
    expected_df = pd.DataFrame(
        {
            'value': [0.0, 1.0, 1.0, 2.0, 3.0, 3.0, 4.0, 5.0, 5.0, 6.0, 7.0, 7.0, 8.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0,],
            'values': [10.0, 10.0, 15.0, 15.0, 15.0, 20.0, 20.0, 20.0, 25.0, 25.0, 25.0, 30.0, 30.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0,],
            'category': ['A', 'A', 'B', 'B', 'B', 'A', 'A', 'A', 'B', 'B', 'B', 'A', 'A', 'A', 'B', 'A', 'B', 'A', 'B',]},
        index=[
            '2023-06-30 00:00:00+00:00',
            '2023-06-30 00:31:00+00:00',
            '2023-06-30 01:00:00+00:00',
            '2023-06-30 01:02:00+00:00',
            '2023-06-30 01:33:00+00:00',
            '2023-06-30 02:00:00+00:00',
            '2023-06-30 02:04:00+00:00',
            '2023-06-30 02:35:00+00:00',
            '2023-06-30 03:00:00+00:00',
            '2023-06-30 03:06:00+00:00',
            '2023-06-30 03:37:00+00:00',
            '2023-06-30 04:00:00+00:00',
            '2023-06-30 04:08:00+00:00',
            '2023-06-30 04:39:00+00:00',
            '2023-06-30 05:00:00+00:00',
            '2023-06-30 06:00:00+00:00',
            '2023-06-30 07:00:00+00:00',
            '2023-06-30 08:00:00+00:00',
            '2023-06-30 09:00:00+00:00',
        ])
    pd.testing.assert_frame_equal(merged_df, expected_df)
    print("All test cases passed!")
