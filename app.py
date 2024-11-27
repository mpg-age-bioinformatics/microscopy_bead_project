import dash
from dash import html, dash_table, dcc
import pandas as pd
import plotly.express as px
from helpers import generate_fig_data

df = pd.read_csv('/mbp/extracted/records.csv')
df = df.assign(date=lambda x: pd.to_datetime(x['date'], format='%Y%m%d'))

fig, considerd_df, change_df, fig_name, warning = generate_fig_data(df, 'AndorDragonfly', '100x1.45', None, None, None, 3, 15)

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Microscopy Bead Project", style={'textAlign': 'center'}),
    # dash_table.DataTable(
    #     id='data-table',
    #     columns=[{"name": i, "id": i} for i in df.columns],
    #     data=df.to_dict('records'),
    #     style_table={'overflowX': 'auto'},
    #     style_header={
    #         'backgroundColor': 'rgb(230, 230, 230)',
    #         'fontWeight': 'bold'
    #     },
    #     style_cell={'textAlign': 'left'}
    # ),
    dcc.Graph(
        id='plotly-figure',
        figure=fig
    )

])

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
