import dash
from dash import html, dash_table, dcc, Input, Output, State, Dash
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
from helpers import generate_fig_data

df = pd.read_csv('/mbp/extracted/records.csv')
df = df.assign(date=lambda x: pd.to_datetime(x['date'], format='%Y%m%d'))

microscope_list = df['microscope'].unique()
objective_list = df['objective'].unique()
test_list = df['test'].unique()
bead_size_list = df['bead_size'].unique()
bead_number_list = df['bead_number'].unique()

fig, considerd_df, change_df, fig_name, warning = generate_fig_data(df, 'AndorDragonfly', '100x1.45', None, None, None, 3, 15)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H2("Microscopy Bead Project", style={'textAlign': 'center'}),
    html.Div([
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                html.H5("Filters", style={"margin-top": 10}),
                                html.Label('Microscope'), dcc.Dropdown( id='opt-microscope', options=[{'label': item, 'value': item} for item in microscope_list]),
                                html.Label('Objective'), dcc.Dropdown( id='opt-objective', options=[{'label': item, 'value': item} for item in objective_list]),
                                html.Label('Test'), dcc.Dropdown( id='opt-test', options=[{'label': item, 'value': item} for item in test_list]),
                                html.Label('Bead Size'), dcc.Dropdown( id='opt-bead-size', options=[{'label': item, 'value': item} for item in bead_size_list]),
                                html.Label('Bead Number'), dcc.Dropdown( id='opt-bead-number', options=[{'label': item, 'value': item} for item in bead_number_list]),
                                # html.Label('Start Date'), dcc.DatePickerSingle(id='date-picker', placeholder='Select a date', style={'margin-bottom': '20px'}),
                                html.Label('Date Range'), html.Br(), dcc.DatePickerRange(id='opt-date', display_format='YYYY-MM-DD'),
                                html.Label('Consider Previous Change Values'), html.Br(), dcc.Input(id='opt-consider-limit', type='number', value=3, min=1, max=50),
                                html.Br(), html.Label('Warning Percentage'), html.Br(), dcc.Input(id='opt-warning-percentage', type='number', value=15, min=1, max=100)
                            ],
                            body=True
                        ),
                        dbc.Button(
                            'Submit',
                            id='submit-button-state',
                            color="secondary",
                            n_clicks=0,
                            style={
                                "width": "100%",
                                "margin-top": "2px",
                                "margin-bottom": "2px"
                            }
                        )
                    ],
                    xs=12, sm=12, md=6, lg=4, xl=3,
                    align="top",
                    style={
                        "padding": "0px",
                        "margin-bottom": "50px"
                    }
                ),

                # Second Column: Markdown Section
                dbc.Col(
                    [
                        html.Div(id="tab-output"),
                    ],
                    xs=12, sm=12, md=6, lg=8, xl=9,
                    style={"margin-bottom": "50px"}
                )
            ],
            align="start",
            justify="left",
            className="g-0",
            style={"width": "100%"}
        )
    ])
])



@app.callback(
    Output("tab-output", "children"),
    Input("submit-button-state", "n_clicks"),
    State("opt-microscope", "value"),
    State("opt-objective", "value"),
    State("opt-test", "value"),
    State("opt-bead-size", "value"),
    State("opt-bead-number", "value"),
    State("opt-date", "start_date"),
    State("opt-date", "end_date"),
    State("opt-consider-limit", "value"),
    State("opt-warning-percentage", "value")
)
def update_output(n_clicks, microscope, objective, test, bead_size, bead_number, start_date, end_date, consider_limit, warning_percentage):
    if not n_clicks:
        return html.Div("Submit to get output!", style={"margin-top": "15px", "margin-left": "15px"})
    
    fig, considerd_df, change_df, fig_name, warning = generate_fig_data(df, microscope, objective, test, start_date, end_date)

    if fig is None or considerd_df is None or change_df is None:
        return html.Div("Fail to generate figure with your input!", style={"margin-top": "15px", "margin-left": "15px"})

    figure_tab = dcc.Graph(
        id='plotly-figure',
        figure=fig
    )

    bead_tab = html.Div("Bead List!")

    considered_tab = dash_table.DataTable(
        id='considered-table',
        columns=[{"name": i, "id": i} for i in considerd_df.columns],
        data=considerd_df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_cell={'textAlign': 'left'}
    )

    change_tab = dash_table.DataTable(
        id='considered-table',
        columns=[{"name": i, "id": i} for i in change_df.columns],
        data=change_df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_cell={'textAlign': 'left'}
    )

    output=dcc.Tabs( 
        [ 
            dcc.Tab(
                dcc.Loading(
                    id="loading-output-1",
                    type="default",
                    children=[ figure_tab ],
                    style={"margin-top":"50%","height": "100%"} 
                ), 
                label="Figure", id="tab-figure",
                style={"margin-top":"0%"}
            ),
            dcc.Tab(
                dcc.Loading(
                    id="loading-output-2",
                    type="default",
                    children=[ considered_tab ],
                    style={"margin-top":"50%","height": "100%"} 
                ), 
                label="Input Data", id="tab-considered",
                style={"margin-top":"0%"}
            ),
            dcc.Tab(
                dcc.Loading(
                    id="loading-output-4",
                    type="default",
                    children=[ change_tab ],
                    style={"margin-top":"50%","height": "100%"} 
                ), 
                label="Deviation", id="tab-change",
                style={"margin-top":"0%"}
            ),
            dcc.Tab(
                dcc.Loading(
                    id="loading-output-3",
                    type="default",
                    children=[ bead_tab ],
                    style={"margin-top":"50%","height": "100%"} 
                ), 
                label="Bead Image", id="tab-bead",
                style={"margin-top":"0%"}
            )
        ]
    )

    return output


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
