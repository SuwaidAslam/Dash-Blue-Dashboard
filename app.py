import dash
from dash import dcc, html, dash_table
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from flask_caching import Cache
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output
from scipy.stats import rayleigh
from db.api import get_top_smallest_data, get_top_largest_data, get_filtered_data, get_unique_security_names_list, get_latest_df


app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})
app.title = "Dashboard"
TIMEOUT = 60 * 60 * 2 # 2 hours

app_color = {"graph_bg": "#082255", "graph_line": "#007ACE"}


security_names_list = get_unique_security_names_list()

def createTable(df):
    """ Helper function to get create a Table from a datafram. """
    table = dash_table.DataTable(
        columns=[{'id': c, 'name': c, "selectable": False,
                  "presentation": "markdown"} for c in df.columns],
        data=df.to_dict('records'),
        page_action='none',
        markdown_options={"html": True},
        fixed_rows={'headers': True},
        style_cell={
            'minWidth': '100px',
            'font-family': 'arial',
            'font-size': '1.2rem',
            'text-align': 'center'
        },
        style_data={
            'whiteSpace': 'normal',
            'height': 'auto',
            'backgroundColor': app_color["graph_bg"],
            'color': 'white'
        },
        style_table={
            'overflowX': 'auto',
            'overflowY': 'auto'
        },
        style_header={
            'backgroundColor': 'rgb(30, 30, 30)',
            'fontWeight': 'bold',
            'color': 'white',
        },
    )
    return table

# --------------- Dashboard Layout ---------------------
app.layout = html.Div(
    [
        # header
        html.Div(
            [
                html.Div(
                    [
                        html.H4("Dashboard", className="app__header__title"),
                        html.P(
                            "This is a dashboard title <placeholer>.",
                            className="app__header__title--grey",
                        ),
                    ],
                    className="app__header__desc",
                ),
                html.Div(
                    [
                        html.A(
                            html.Img(
                                src=app.get_asset_url("dash-new-logo.png"),
                                className="app__menu__img",
                            ),
                            href="https://plotly.com/dash/",
                        ),
                    ],
                    className="app__header__logo",
                ),
            ],
            className="app__header",
        ),
        html.Div(
            [
                # top negative and positive tables
                html.Div(
                    [
                        dcc.Interval(id='interval', max_intervals=0, n_intervals=0),
                        html.Div(
                            [html.H6("Top Values Tables", className="graph__title")]
                        ),
                        dcc.Loading([
                                html.Div(
                                    [
                                        html.H6("Top 15 Positive Data", className="graph__title"),
                                        html.Div(id='positive_table')
                                    ], className="six columns", style={'padding-left':'1%'},
                                ),
                                html.Div(
                                    [
                                        html.H6("Top 15 Negative Data", className="graph__title"),
                                        html.Div(id='negative_table')
                                    ], className="six columns"
                                ),
                        ], className="twelve columns tables")
                    ],
                    className="twelve columns tables__container",
                ),
                # subplot
                html.Div(
                    [
                        html.Div(
                            [html.H6("Datetime Subplots", className="graph__title")]
                        ),
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id="security_name_dropdown",
                                    options=security_names_list,
                                        value=security_names_list[0]
                                )
                            ],
                            className="dropdown",
                        ),
                        dcc.Loading([
                            dcc.Graph(
                                id="subplot",
                                figure=dict(
                                    layout=dict(
                                        plot_bgcolor=app_color["graph_bg"],
                                        paper_bgcolor=app_color["graph_bg"],
                                    )
                                ),
                            ),
                            html.Div(id='subplot_table', style={'padding-left' : '10px', 'padding-right' : '10px'}),
                        ]),
                    ],
                    className="twelve columns subplots__container",
                ),
            ],
            className="app__content",
        ),
    ],
    className="app__container",
)



# ------------- Callback Methods ----------------
@app.callback(
    Output("subplot", "figure"), 
    Output('subplot_table', 'children'), 
    [Input("security_name_dropdown", "value")]
)
@cache.memoize(timeout=TIMEOUT)
def gen_subplot(security_name):
    """
    Generate the subplot graph.

    :params security_name: update the graph based on the selected security name
    """
    df = get_filtered_data(security_name)
    if df is not None:
        fig = make_subplots(rows=3, cols=1,
            vertical_spacing = 0.2,
            specs=[[{}],
            [{}],
            [{}]])

        fig.append_trace(go.Scatter(
            x=df['datetime'],
            y=df['lending_pool'],
            textposition="top center",
            name="Lending Pool",
        ), row=1, col=1)

        fig.append_trace(go.Scatter(
            x=df['datetime'],
            y=df['borrowing_rate'],
            textposition="top center",
            name="Borrowing Rate",
        ), row=2, col=1)

        fig.append_trace(go.Scatter(
            x=df['datetime'],
            y=df['borrowed'],
            textposition="top center",
            name="Borrowed",
        ), row=3, col=1)

        fig.update_xaxes(title_text="DateTime", type='date',
                        tickformat = "%H:%M\n%b %d, %Y",
                        tickangle=0,
                        autorange= True)
        fig.update_yaxes(title_text="Lending Pool", row=1, col=1)
        fig.update_yaxes(title_text="Borrowing Rate", row=2, col=1)
        fig.update_yaxes(title_text="Borrowed", row=3, col=1)

        fig.update_layout(
            plot_bgcolor=app_color["graph_bg"],
            paper_bgcolor=app_color["graph_bg"],
            font={"color": "#fff"},
            height=1000,
            showlegend=False,
        )
        table = createTable(df)
        return fig, table
    else:
        raise PreventUpdate


@app.callback(
    Output("positive_table", "children"), 
    Output('negative_table', 'children'), 
    [Input("interval", "n_intervals")]
)
def gen_top_tables(n_intervals):
    """
    Generate the two top negative and positive tables.

    :params security_name: update the graph based on the selected security name
    """
    latest_hour_df = get_latest_df()
    top_positive_table = createTable(get_top_largest_data(latest_hour_df))
    top_negative_table = createTable(get_top_smallest_data(latest_hour_df))
    return top_positive_table, top_negative_table


if __name__ == "__main__":
    app.run_server(debug=False)
