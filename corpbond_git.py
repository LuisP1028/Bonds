import pandas as pd
import smtplib
from email.mime.text import MIMEText
from fredapi import Fred
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import dash_bootstrap_components as dbc

# Define your FRED API key and series IDs
api_key = ''
series_ids = [
    "BAMLH0A3HYCEY", 
    "BAMLC0A0CMEY", 
    "BAMLC0A4CBBBEY", 
    "BAMLC0A1CAAAEY", 
    "NASDAQ100",
    "IRLTLT01CHM156N"
]

# Create a dictionary for user-friendly names
series_names = {
    "BAMLC0A0CMEY": "Corporate Index Yield",
    "BAMLH0A3HYCEY":  "CCC & Lower Yield",
    "BAMLC0A4CBBBEY": "BBB Yield, AT&T, Ford, GM",
    "BAMLC0A1CAAAEY": "AAA Yield, Microsoft, Apple, ExxonMobil",
    "NASDAQ100": "NASDAQ 100 Index",
    "IRLTLT01CHM156N": "10y Swiss Bond Yield"
}

# Create a dictionary to store thresholds for each series
thresholds = {
    "BAMLC0A0CMEY": 1.5,
    "BAMLH0A3HYCEY": 0.6,
    "BAMLC0A4CBBBEY": 1.3,
    "BAMLC0A1CAAAEY": 1.3,
    "NASDAQ100": 2.5,
    "IRLTLT01CHM156N": 1
}

# Email parameters
smtp_server = ''
smtp_port = 
sender_email = ''  # Your email
sender_password = ''  # Your App Password
recipient_email = ''  # Your email

def send_email_alert(instrument_name, threshold, current_value):
    subject = f"Alert: {instrument_name} crossed the threshold!"
    body = f"The instrument {instrument_name} has crossed the threshold of {threshold}.\n" \
           f"Current standardized value: {current_value}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"Email sent successfully to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def fetch_data_from_fred(api_key, series_id):
    fred = Fred(api_key=api_key)
    data = fred.get_series(series_id)
    data = pd.DataFrame(data, columns=[series_id])
    data['date'] = data.index
    data.reset_index(drop=True, inplace=True)
    return data

def calculate_first_difference_and_standardize(data, column):
    first_difference = data[column].diff()
    standardized_diff = (first_difference - first_difference.mean()) / first_difference.std()
    data[f'{column}_first_diff_zscore'] = standardized_diff

    # Get the specific threshold for the series
    threshold = thresholds[column]

    # Check if the threshold is crossed and send an email alert
    latest_value = standardized_diff.iloc[-1]
    if abs(latest_value) > threshold:
        instrument_name = series_names[column]
        send_email_alert(instrument_name, threshold, latest_value)

    return data

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("FRED Data Dashboard"),
            html.Label("Select Dataset"),
            dcc.Dropdown(
                id='dataset1',
                options=[{'label': series_names[key], 'value': key} for key in series_ids],
                value=series_ids[0]  # Default selection
            ),
            html.Div(id='threshold-container'),
            html.Div(id="graph-container")
        ], width=12)
    ])
])

@app.callback(
    Output("threshold-container", "children"),
    [Input("dataset1", "value")]
)
def update_threshold_input(selected_dataset):
    # Get the current threshold for the selected dataset
    threshold_value = thresholds[selected_dataset]
    return html.Div([
        html.Label(f"Set Threshold for {series_names[selected_dataset]}"),
        dcc.Input(
            id='threshold-input',
            type='number',
            value=threshold_value,  # Default threshold value
            step=0.1,
            min=0
        )
    ])

@app.callback(
    Output("graph-container", "children"),
    [Input("dataset1", "value"),
     Input("threshold-input", "value")]
)
def update_graph(selected_dataset, threshold):
    # Update the threshold for the selected dataset in the thresholds dictionary
    thresholds[selected_dataset] = threshold
    
    # Fetch and process data for the selected dataset
    data = fetch_data_from_fred(api_key, selected_dataset)
    data = calculate_first_difference_and_standardize(data, selected_dataset)
    return dcc.Graph(figure=create_plotly_graph(data, selected_dataset, series_names[selected_dataset], threshold))

def create_plotly_graph(data, column, friendly_name, threshold):
    trace = go.Scatter(
        x=data['date'],
        y=data[f'{column}_first_diff_zscore'],
        mode='lines',
        name=f'{friendly_name} Z-Score'
    )
    
    layout = go.Layout(
        title=f'Standardized First Difference of {friendly_name}',
        xaxis={'title': 'Date'},
        yaxis={'title': 'Standardized Value (Z-Score)'},
        shapes=[
            {'type': 'line', 'x0': data['date'].min(), 'x1': data['date'].max(), 'y0': threshold, 'y1': threshold,
             'line': {'color': 'red', 'width': 2, 'dash': 'dash'}},
            {'type': 'line', 'x0': data['date'].min(), 'x1': data['date'].max(), 'y0': -threshold, 'y1': -threshold,
             'line': {'color': 'red', 'width': 2, 'dash': 'dash'}}
        ]
    )
    
    return {'data': [trace], 'layout': layout}

# Send a test email when the script is run
def send_test_email():
    subject = "Test Email from Python Script"
    body = "This is a test email to confirm the SMTP setup works correctly."
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"Test email sent successfully to {recipient_email}")
    except Exception as e:
        print(f"Failed to send test email: {e}")

if __name__ == '__main__':
    # Send a test email
    send_test_email()

    # Run the Dash app
    app.run_server(debug=True)