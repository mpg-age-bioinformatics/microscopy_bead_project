import os
import glob
import pandas as pd
import plotly.express as px
from datetime import datetime


# Filter dataframe
# Return: filtered dataframe
def fetch_df(df, microscope=None, objective=None, test=None, bead_size=None, bead_number=None, start_date=None, end_date=None):
    # filter df by date if provided
    try:
        if datetime.strptime(start_date, '%Y-%m-%d') and datetime.strptime(end_date, '%Y-%m-%d'):
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    except:
        pass
    if microscope is not None:
        df = df[df['microscope'] == microscope]
    if objective is not None:
        df = df[df['objective'] == objective]
    if test is not None:
        df = df[df['test'] == test]
    if bead_size is not None:
        df = df[df['bead_size'] == bead_size]
    if bead_number is not None:
        df = df[df['bead_number'] == bead_number]
        
    return df


# Generate figure, considered value and warning
# Return: figure, data, change, title, warning
def generate_fig_data(df, microscope=None, objective=None, test=None, bead_size=None, bead_number=None, start_date=None, end_date=None, consider_limit=3, warning_percentage=15):
    try:
        # fetch dataframe
        fdf = fetch_df(df, microscope, objective, test, bead_size, bead_number, start_date, end_date)
        if fdf.empty:
            return None, None, None, None, None

        # defined values
        columns_to_mean = ['far_red', 'red', 'uv', 'dual']
        warning = False
        sd_data = []
        color_map = {
            'far_red': 'orange',
            'red': 'red',
            'uv': 'blue',
            'dual': 'green'
        }

        # get fig name
        fig_name = "FIG"
        fig_name += f"_{microscope}" if microscope else ""
        fig_name += f"_{objective}" if objective else ""
        fig_name += f"_{test}" if test else ""
        fig_name += f"_{str(start_date)}" if start_date else ""
        fig_name += f"_{str(end_date)}" if end_date else ""

        # get mean and deviation
        columns_to_mean = [col for col in columns_to_mean if not fdf[col].isna().all()]
        stats_df = fdf[['date'] + columns_to_mean].groupby('date').agg(['mean', 'std']).reset_index()
        stats_df.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in stats_df.columns]

        for col in columns_to_mean:
            sd_data.append({
                'date': stats_df['date'],
                'mean': stats_df[f'{col}_mean'],
                'std': stats_df[f'{col}_std'],
                'metric': col
            })

        proc_df = pd.concat(
            [pd.DataFrame(err) for err in sd_data],
            axis=0
        ).reset_index(drop=True)

        # sort the DataFrame by date to identify the most recent dates
        stats_df = stats_df.sort_values('date')

        # identify the last date and the earlier available dates
        last_date = stats_df['date'].max()
        available_dates = stats_df['date'].unique()
        num_earlier_dates = min(consider_limit, len(available_dates) - 1)  # Use up to consider_limit dates or all available earlier dates

        # select the earlier dates
        earlier_dates = stats_df['date'].nlargest(num_earlier_dates + 1).iloc[1:]

        # filter data for the earlier dates
        last_n_data = stats_df[stats_df['date'].isin(earlier_dates)]

        # calculate the mean for the selected earlier dates
        last_n_mean = last_n_data[[f'{col}_mean' for col in columns_to_mean]].mean()

        # get the last date's values
        last_date_data = stats_df[stats_df['date'] == last_date]
        last_date_values = last_date_data[[f'{col}_mean' for col in columns_to_mean]].values[0]

        # calculate the percentage change
        percentage_change = (last_date_values - last_n_mean.values) / last_n_mean.values * 100

        # create a result DataFrame
        change_df = pd.DataFrame({
            'Metric': columns_to_mean,
            f"Up To {consider_limit} Dates Mean": last_n_mean.values,
            'Last Date Mean': last_date_values,
            'Percentage Change (%)': percentage_change
        })

        # check if the percentage change is more than warning_percentage
        significant_changes = change_df[change_df['Percentage Change (%)'].abs() > warning_percentage]
        warning = True if not significant_changes.empty else False

        if warning:
            title_content = f"🔴🔴🔴 {fig_name} 🔴🔴🔴"
        else:
            title_content = f"🟢🟢🟢 {fig_name} 🟢🟢🟢"

        # generate figure
        fig = px.line(
            proc_df,
            x='date',
            y='mean',
            error_y='std',
            color='metric',
            color_discrete_map=color_map,
            labels={'mean': 'Value', 'date': 'Date', 'metric': 'Metric'},
            markers=True
        )

        fig.update_layout(
            title=dict(
                text=title_content,
                x=0.5,  # Center align
                xanchor='center'
            )
        )

        return fig, fdf, change_df, fig_name, warning
    except:
        return None, None, None, None, None
    
# Get the list of image relative paths
# Return: list
def get_image_paths(input_path, base_path = "/mcs_bead_project/data/"):
    # Extract the directory from the input path
    directory = os.path.dirname(input_path)
    
    # Use glob to find all .jpg files in the directory
    image_files = glob.glob(os.path.join(directory, "*.jpg"))
    relative_paths = [path.replace(base_path, "") for path in image_files]
    
    return relative_paths
    
