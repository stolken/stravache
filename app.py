# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd
from stravaio import strava_oauth2, StravaIO
import json
import matplotlib as plt
import seaborn as sns


def get_client():
    access_token = "bcd443cb366993800605e853db527df1cfe33aae"
    client = StravaIO(access_token=access_token)
    return client


client = get_client()


def get_activity_stream_dataframe(athlete_id=94046257, id=8146797672):
    streams = client.get_activity_streams(athlete_id=athlete_id, id=id)
    df = pd.DataFrame(streams.to_dict())
    #act_stream["efficiency"] = act_stream["velocity_smooth"] / act_stream["heartrate"]
    return df


def get_activity_heartrate_mean(athlete_id=94046257, id=8146797672):
    client = get_client()
    try:
        streams = client.get_activity_streams(athlete_id=athlete_id, id=id)
        df = pd.DataFrame(streams.to_dict())
        get_activity_heartrate_mean = df.heartrate.mean()
    except Exception as e:
        if e.status == 404:
            get_activity_heartrate_mean = 0
        else:
            raise Exception("Exception")

    return get_activity_heartrate_mean


def get_activities_using_cache():
    print("get_activities_using_cache")
    from pathlib import Path
    client = get_client()
    list_activities = client.get_logged_in_athlete_activities(
        after='10-01-2022')
    existing_ids = list()

    parquet_file = Path("strava_activities.parquet")
    if parquet_file.is_file():
        activities_df = pd.read_parquet(parquet_file)
        existing_ids = activities_df['id'].values
    else:
        activities_df = pd.DataFrame()

    for act in list_activities:
        if not str(act.id) in existing_ids:
            act_df = pd.json_normalize(act.to_dict())
            act_df["moving_time_minute"] = act_df["moving_time"] / 60
            act_df["distance_km"] = act_df["distance"] / 1000
            act_df["heartrate_mean"] = get_activity_heartrate_mean(
                athlete_id=act.athlete.id, id=act.id)

            activities_df = pd.concat([activities_df, act_df])
            activities_df['id'] = activities_df['id'].apply(
                lambda x: x if pd.isnull(x) else str(int(x)))
            print("New activity " + str(act.id))
            activities_df.to_parquet(parquet_file)
    return activities_df


app = Dash(__name__)

df = get_activities_using_cache()

df_thisyear = df.loc[df.start_date_local  > "2022-01-06",['start_date_local',"distance_km","moving_time"]]
df_thisyear_week_summary = df_thisyear.groupby([df_thisyear['start_date_local'].dt.isocalendar().week]).agg({'distance_km': ['sum', 'max']})
df_thisyear_week_summary.columns = df_thisyear_week_summary.columns.droplevel()


time_distance_heartrate_graph_fig = px.scatter(df, x="moving_time_minute", y="distance_km", color="heartrate_mean", size="heartrate_mean")

#df_2022_week_summary_km.plot.bar(figsize=(30, 10))
thisyear_weekly_volume_graph_fig = px.bar(df_thisyear_week_summary, barmode = 'group')

app.layout = html.Div(children=[
    html.H1(children='Stravache Analysis'),

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),

    dcc.Graph(
        id='time_distance_heartrate-graph',
        figure=time_distance_heartrate_graph_fig
    ),
    dcc.Graph(
        id='thisyear_weekly_volume-graph',
        figure=thisyear_weekly_volume_graph_fig
    )
])


if __name__ == '__main__':

    app.run_server(debug=True)
