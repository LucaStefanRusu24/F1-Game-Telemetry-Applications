import dash
from dash import dcc, html
import plotly.graph_objs as go
import threading
from flask import Flask
from telemetry_listener import receive_telemetry, parse_telemetry_packet
from dash.dependencies import Output, Input 

# Initialize the Dash app
server = Flask(__name__)
app = dash.Dash(__name__, server=server)

# Layout of the dashboard
app.layout = html.Div([
    html.H1("F1 Telemetry Dashboard"),
    
    # Speed bar
    dcc.Graph(id="live-speed"),

    # Throttle bar
    dcc.Graph(id="throttle"),

    # Brake bar
    dcc.Graph(id="brake"),

    # Auto-update interval (refreshes every 500ms)
    dcc.Interval(id="interval-update", interval=500, n_intervals=0)
])

# Global variable to hold telemetry data
telemetry_data = {"speed": 0, "throttle": 0, "brake": 0, "gear": 0, "lap_time": 0}

@app.callback(
    [Output("live-speed", "figure"),
     Output("throttle", "figure"),  
     Output("brake", "figure")],
    [Input("interval-update", "n_intervals")]
)
def update_graphs(n):
    global telemetry_data

    # Speed bar graph
    speed_fig = go.Figure()
    speed_fig.add_trace(go.Bar(y=["Speed"], x=[telemetry_data["speed"]], orientation='h'))
    speed_fig.update_layout(title="Speed (km/h)", xaxis=dict(range=[0, 350]))

    # Throttle bar graph
    throttle_fig = go.Figure()
    throttle_fig.add_trace(go.Bar(y=["Throttle"], x=[telemetry_data["throttle"]], orientation='h'))
    throttle_fig.update_layout(title="Throttle", xaxis=dict(range=[0, 1]))

    # Brake bar graph
    brake_fig = go.Figure()
    brake_fig.add_trace(go.Bar(y=["Brake"], x=[telemetry_data["brake"]], orientation='h'))
    brake_fig.update_layout(title="Brake", xaxis=dict(range=[0, 1]))

    return speed_fig, throttle_fig, brake_fig

def telemetry_thread():
    """
    This function continuously receives telemetry data
    and updates the global telemetry_data dictionary.
    """
    global telemetry_data
    while True:
        data = receive_telemetry()
        telemetry_data.update(parse_telemetry_packet(data))

# Run the telemetry receiver in a separate thread
thread = threading.Thread(target=telemetry_thread)
thread.daemon = True
thread.start()

# Start the Dash web app
if __name__ == "__main__":
    app.run_server(debug=False, use_reloader=False)
