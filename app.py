import dash
import os
import logging
import threading
from dash import html, dash_table, dcc, Input, Output, State, Dash
import pandas as pd
import plotly.express as px
from pathlib import Path
from flask import send_file, abort, g, has_request_context
import dash_bootstrap_components as dbc
from helpers import generate_fig_data, get_image_paths
from admin import register_admin
from auth import register_auth
from data_paths import get_data_paths
from downloads import register_downloads
from log_config import configure_logging

# Define values
data_paths = get_data_paths()
base_data_path = data_paths.source_dir
records_path = os.path.join(data_paths.extracted_dir, "records.csv")
record_columns = [
    "date", "microscope", "objective", "test", "bead_size", "bead_number",
    "far_red", "red", "uv", "dual", "x", "y", "z",
    "uniformity", "field_uniformity", "centering_accuracy", "file_path"
]

configure_logging()
logger = logging.getLogger("app")

# Cache complete snapshots; the extractor publishes records.csv atomically.
_records_lock = threading.Lock()
_records_version = None
_records_df = pd.DataFrame(columns=record_columns)


def get_records():
    global _records_df, _records_version
    with _records_lock:
        try:
            stat = os.stat(records_path)
            version = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
            if version != _records_version:
                refreshed = pd.read_csv(records_path)
                if not set(record_columns).issubset(refreshed.columns):
                    raise ValueError("records.csv is missing required columns")
                refreshed['date'] = pd.to_datetime(refreshed['date'], format='%Y%m%d', errors='coerce')
                _records_df = refreshed
                _records_version = version
        except FileNotFoundError:
            pass  # Start with empty filters until the first extraction completes.
        except Exception:
            logger.exception("Failed to reload %s; retaining the previous dataset.", records_path)
        return _records_df


def to_options(series):
    # Build dropdown options, dropping NaN so the dropdown never receives a
    # null option. Hom/CenHom rows have empty bead_size/bead_number (read as
    # NaN), which Dash rejects as an invalid option. Labels are stringified
    # (Dash expects string/number labels), values kept native for filtering.
    def fmt(v):
        # NaN in a column forces float dtype, so whole numbers arrive as e.g.
        # 7.0; show them as "7" rather than "7.0".
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v)
    return [{'label': fmt(v), 'value': v} for v in series.dropna().unique()]

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server
account_store = register_auth(server)
update_manager = register_admin(server, data_paths, account_store)
register_downloads(server, data_paths)

# Flask route to serve images
@server.route('/images/<path:image_name>')
def serve_image(image_name):
    base = Path(base_data_path).resolve()
    image_path = (base / image_name).resolve()
    if not image_path.is_relative_to(base) or not image_path.is_file():
        abort(404)
    return send_file(image_path)

def dashboard_layout():
    df = get_records()
    user = getattr(g, "user", None) if has_request_context() else None
    navigation = [html.A("Account / sign out", href="/account")]
    if user and user['role'] == 'admin':
        navigation.insert(0, html.A("Downloads", href="/download", style={"marginRight": "20px"}))
        navigation.insert(0, html.A("Admin", href="/admin", style={"marginRight": "20px"}))
    return html.Div([
        dcc.Interval(id="records-refresh", interval=15000, n_intervals=0),
        html.Div(navigation, style={"textAlign": "right", "padding": "8px 16px"}),
        html.H2("Microscopy Bead Project", style={'textAlign': 'center'}),
        html.Div([
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    html.H5("Filters", style={"margin-top": 10}),
                                    html.Label('Microscope'), dcc.Dropdown( id='opt-microscope', options=to_options(df['microscope'])),
                                    html.Label('Objective'), dcc.Dropdown( id='opt-objective', options=to_options(df['objective'])),
                                    html.Label('Test'), dcc.Dropdown( id='opt-test', options=to_options(df['test'])),
                                    html.Label('Bead Size'), dcc.Dropdown( id='opt-bead-size', options=to_options(df['bead_size'])),
                                    html.Label('Bead Number'), dcc.Dropdown( id='opt-bead-number', options=to_options(df['bead_number'])),
                                    # html.Label('Start Date'), dcc.DatePickerSingle(id='date-picker', placeholder='Select a date', style={'margin-bottom': '20px'}),
                                    html.Label('Date Range'), html.Br(), dcc.DatePickerRange(id='opt-date', display_format='YYYY-MM-DD'),
                                    html.Label('Consider Previous Values for Line Deviation'), html.Br(), dcc.Input(id='opt-consider-limit', type='number', value=3, min=1, max=50),
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


app.layout = dashboard_layout


@app.callback(
    Output("opt-microscope", "options"),
    Output("opt-objective", "options"),
    Output("opt-test", "options"),
    Output("opt-bead-size", "options"),
    Output("opt-bead-number", "options"),
    Input("records-refresh", "n_intervals"),
)
def refresh_filters(_):
    df = get_records()
    return [to_options(df[column]) for column in
            ("microscope", "objective", "test", "bead_size", "bead_number")]



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

    logger.info(
        "Output request: microscope=%s objective=%s test=%s bead_size=%s bead_number=%s "
        "dates=%s..%s consider_limit=%s warning_pct=%s",
        microscope, objective, test, bead_size, bead_number,
        start_date, end_date, consider_limit, warning_percentage
    )

    fig, considerd_df, change_df, fig_name, warning = generate_fig_data(get_records(), microscope, objective, test, bead_size, bead_number, start_date, end_date, consider_limit, warning_percentage)

    if fig is None or considerd_df is None or change_df is None:
        logger.warning("No data/figure produced for the requested filters.")
        return html.Div("No data found with the inputs!", style={"margin-top": "15px", "margin-left": "15px"})

    figure_tab = dcc.Graph(
        id='plotly-figure',
        figure=fig
    )

    bead_tab = html.Div(
        [
            # Loop through bead paths to generate sections
            html.Div(
                [
                    html.H6(os.path.dirname(bead_path), style={'textAlign': 'center'}),  # Bead path header

                    # Display images for this bead path
                    html.Div(
                        [
                            html.Img(
                                src=f"/images/{image}",  # Replace with actual image path logic
                                title=os.path.basename(image),
                                style={"max-width": "400px", "max-height": "400px", "margin": "10px", "object-fit": "contain"}
                            )
                            for image in get_image_paths(bead_path, base_data_path + os.sep)
                        ],
                        style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"}
                    )
                ],
                style={"margin-bottom": "30px"}  # Add spacing between bead sections
            )
            for bead_path in considerd_df['file_path']
        ]
    )

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
                label="Data", id="tab-considered",
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
                label="Image", id="tab-bead",
                style={"margin-top":"0%"}
            )
        ]
    )

    return output


if __name__ == '__main__':
    logger.info("Starting Dash app on http://0.0.0.0:8050")
    app.run_server(debug=False, host='0.0.0.0', port=8050)
