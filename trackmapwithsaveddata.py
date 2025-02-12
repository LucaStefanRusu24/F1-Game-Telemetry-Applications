import dash
from dash import dcc, html, dash_table
import plotly.graph_objs as go
import threading
import pandas as pd
import json
import os
from flask import Flask
from telemetry_listener import receive_telemetry, parse_telemetry_packet
from dash.dependencies import Output, Input

# Initialize the Dash app
server = Flask(__name__)
app = dash.Dash(__name__, server=server)

TRACKS = {
    0: "melbourne", 1: "paul_ricard", 2: "shanghai", 3: "sakhir",
    4: "catalunya", 5: "monaco", 6: "montreal", 7: "silverstone",
    8: "hockenheim", 9: "hungaroring", 10: "spa", 11: "monza",
    12: "singapore", 13: "suzuka", 14: "abu_dhabi", 15: "texas",
    16: "brazil", 17: "austria", 18: "sochi", 19: "mexico",
    20: "baku", 21: "sakhir_short", 22: "silverstone_short",
    23: "texas_short", 24: "suzuka_short", 25: "hanoi", 26: "zandvoort",
    27: "imola", 28: "portimao", 29: "jeddah", 30: "miami", 31: "las_vegas"
}

DEFAULT_TRACK = "monaco"

WORLD_COORDS = {
    "monaco": {"x_min": -1500, "x_max": 1500, "y_min": -1500, "y_max": 1500},
    "monza": {"x_min": -2000, "x_max": 2000, "y_min": -2000, "y_max": 2000},
    "silverstone": {"x_min": -2500, "x_max": 2500, "y_min": -2500, "y_max": 2500},
    "spa": {"x_min": -3000, "x_max": 3000, "y_min": -3000, "y_max": 3000}
}

# Stores past positions for lap tracing
lap_trace = []

# Directory for session data
SESSION_DIR = "sessions"
os.makedirs(SESSION_DIR, exist_ok=True)

# Global variable to store telemetry data logs
telemetry_log = []

# Layout of the dashboard
app.layout = html.Div([
    html.H1("F1 Telemetry Dashboard"),
    
    dcc.Tabs(id="tabs", value="real-time", children=[
        dcc.Tab(label="Live Telemetry", value="real-time"),
        dcc.Tab(label="Session Review", value="review")
    ]),
    
    html.Div(id="tab-content"),
    
    # Interval for real-time updates
    dcc.Interval(id="interval-update", interval=500, n_intervals=0)
])

# Global telemetry data
telemetry_data = {"speed": 0, "throttle": 0, "brake": 0, "gear": 0, "lap_time": 0, "x": 0, "y": 0, "track_id": -1}

def map_world_to_image(world_x, world_y, track_name):
    """ Converts world coordinates from telemetry into pixel positions on the track map. """
    if track_name not in WORLD_COORDS:
        track_name = DEFAULT_TRACK  # Default to Monaco if track not found

    world_range = WORLD_COORDS[track_name]

    # Normalize to a scale between 0 and 1
    norm_x = (world_x - world_range["x_min"]) / (world_range["x_max"] - world_range["x_min"])
    norm_y = (world_y - world_range["y_min"]) / (world_range["y_max"] - world_range["y_min"])

    # Scale to image size (assuming image is 2000x2000 pixels)
    image_x = -1000 + norm_x * 2000
    image_y = 1000 - norm_y * 2000  # Invert Y for correct positioning

    return image_x, image_y


@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(selected_tab):
    """ Updates the UI based on selected tab. """
    if selected_tab == "real-time":
        return html.Div([
            dcc.Graph(id="live-speed"),
            dcc.Graph(id="throttle"),
            dcc.Graph(id="brake"),
            dcc.Graph(id="track-map"),
            html.Button("Save & Analyze Data", id="save-button", n_clicks=0)
        ])
    
    elif selected_tab == "review":
        return html.Div([
            html.H3("Select Session"),
            dcc.Dropdown(id="session-dropdown", options=get_session_options(), value=None),
            dcc.Graph(id="session-speed"),
            dcc.Graph(id="session-throttle"),
            dcc.Graph(id="session-brake"),
            dcc.Graph(id="session-lap-time")
        ])


def get_session_options():
    """ Returns available saved sessions for dropdown selection. """
    files = [f for f in os.listdir(SESSION_DIR) if f.endswith(".csv")]
    return [{"label": f.replace(".csv", ""), "value": f} for f in files]


@app.callback(
    Output("save-button", "children"),
    Input("save-button", "n_clicks")
)
def save_telemetry_data(n_clicks):
    """ Saves telemetry data to a JSON and CSV file for later analysis. """
    if n_clicks > 0 and telemetry_log:
        session_name = f"session_{len(os.listdir(SESSION_DIR))}"
        df = pd.DataFrame(telemetry_log)

        # Save as CSV
        csv_path = os.path.join(SESSION_DIR, f"{session_name}.csv")
        df.to_csv(csv_path, index=False)

        # Save as JSON
        json_path = os.path.join(SESSION_DIR, f"{session_name}.json")
        with open(json_path, "w") as f:
            json.dump(telemetry_log, f, indent=4)

        return f"Session Saved: {session_name} "

    return "Save & Analyze Data"


@app.callback(
    [Output("session-speed", "figure"),
     Output("session-throttle", "figure"),
     Output("session-brake", "figure"),
     Output("session-lap-time", "figure")],
    Input("session-dropdown", "value")
)
def load_session_data(selected_session):
    """ Loads session data and generates graphs. """
    if not selected_session:
        return [go.Figure(), go.Figure(), go.Figure(), go.Figure()]

    df = pd.read_csv(os.path.join(SESSION_DIR, selected_session))

    # Speed Graph
    speed_fig = go.Figure()
    speed_fig.add_trace(go.Scatter(y=df["speed"], mode="lines", name="Speed (km/h)"))
    speed_fig.update_layout(title="Speed Over Time")

    # Throttle Graph
    throttle_fig = go.Figure()
    throttle_fig.add_trace(go.Scatter(y=df["throttle"], mode="lines", name="Throttle"))
    throttle_fig.update_layout(title="Throttle Over Time")

    # Brake Graph
    brake_fig = go.Figure()
    brake_fig.add_trace(go.Scatter(y=df["brake"], mode="lines", name="Brake"))
    brake_fig.update_layout(title="Brake Over Time")

    # Lap Time Graph
    lap_time_fig = go.Figure()
    lap_time_fig.add_trace(go.Scatter(y=df["lap_time"], mode="lines", name="Lap Time"))
    lap_time_fig.update_layout(title="Lap Time Progression")

    return speed_fig, throttle_fig, brake_fig, lap_time_fig


@app.callback(
    [Output("live-speed", "figure"),
     Output("throttle", "figure"),
     Output("brake", "figure"),
     Output("track-map", "figure")],
    [Input("interval-update", "n_intervals")]
)

def update_graphs(n):
    global telemetry_data, lap_trace

    # Get track name from track ID, default to Monaco if track ID is unknown
    track_name = TRACKS.get(telemetry_data.get("track_id", -1), DEFAULT_TRACK)

    # Path to the correct track image
    track_image_path = f"assets/{track_name}.png"

    # Convert world coordinates to image position
    mapped_x, mapped_y = map_world_to_image(telemetry_data["x"], telemetry_data["y"], track_name)

    # Store past positions for lap tracing
    if len(lap_trace) > 500:  # Limit stored points to avoid performance issues
        lap_trace.pop(0)
    lap_trace.append((mapped_x, mapped_y))

    # Speed bar graph
    speed_fig = go.Figure()
    speed_fig.add_trace(go.Bar(y=["Speed"], x=[telemetry_data["speed"]], orientation='h'))
    speed_fig.update_layout(title="Speed (km/h)", xaxis=dict(range=[0, 350], fixedrange=True))

    # Throttle bar graph
    throttle_fig = go.Figure()
    throttle_fig.add_trace(go.Bar(y=["Throttle"], x=[telemetry_data["throttle"]], orientation='h'))
    throttle_fig.update_layout(title="Throttle", xaxis=dict(range=[0, 1], fixedrange=True))

    # Brake bar graph
    brake_fig = go.Figure()
    brake_fig.add_trace(go.Bar(y=["Brake"], x=[telemetry_data["brake"]], orientation='h'))
    brake_fig.update_layout(title="Brake", xaxis=dict(range=[0, 1], fixedrange=True))

    # Track Map Graph
    track_fig = go.Figure()

    # Add the correct track map background image
    track_fig.add_layout_image(
        dict(
            source=track_image_path,  # Uses the correct image based on track_id
            xref="x",
            yref="y",
            x=-1000,
            y=1000,
            sizex=2000,
            sizey=2000,
            xanchor="left",
            yanchor="top",
            layer="below"
        )
    )

    # Add past lap positions as a line trace
    if len(lap_trace) > 1:
        track_fig.add_trace(go.Scatter(
            x=[p[0] for p in lap_trace],
            y=[p[1] for p in lap_trace],
            mode="lines",
            name="Lap Trace",
            line=dict(color="blue", width=2)
        ))

    # Add car position (Live tracking)
    track_fig.add_trace(go.Scatter(
        x=[mapped_x],
        y=[mapped_y],
        mode="markers",
        name="Car",
        marker=dict(color="red", size=10)
    ))

    # Fix the zoom level
    track_fig.update_layout(
        title=f"Track Map - {track_name.capitalize()}",
        xaxis=dict(showgrid=False, zeroline=False, range=[-1000, 1000], fixedrange=True),
        yaxis=dict(showgrid=False, zeroline=False, range=[-1000, 1000], fixedrange=True),
        showlegend=True
    )

    return speed_fig, throttle_fig, brake_fig, track_fig



def telemetry_thread():
    """ Continuously receives telemetry data and logs it. """
    global telemetry_data
    while True:
        data = receive_telemetry()
        telemetry_data.update(parse_telemetry_packet(data))


# Start telemetry thread
thread = threading.Thread(target=telemetry_thread)
thread.daemon = True
thread.start()

# Start Dash app
if __name__ == "__main__":
    app.run_server(debug=False, use_reloader=False)
