# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd
from stravaio import strava_oauth2, StravaIO
import json
import matplotlib as plt
import seaborn as sns
import datetime


def get_client():
    access_token = "f323415afa8977b09464adacc6d72617a7c58062"
    client = StravaIO(access_token=access_token)
    return client


client = get_client()


def get_activity_stream_dataframe(athlete_id=94046257, id=8146797672):
    streams = client.get_activity_streams(athlete_id=athlete_id, id=id)
    df = pd.DataFrame(streams.to_dict())
    #act_stream["efficiency"] = act_stream["velocity_smooth"] / act_stream["heartrate"]
    return df


def get_activity_heartrate_mean(athlete_id=94046257, id=8146797672):
    get_activity_heartrate_mean = 0
    client = get_client()
    try:
        streams = client.get_activity_streams(athlete_id=athlete_id, id=id)
    except Exception as e:
        if e.status == 404:
            pass
        else:
            raise Exception("Exception")
    else:
        df = pd.DataFrame(streams.to_dict())
        if "heartrate" in df.columns:
            get_activity_heartrate_mean = df.heartrate.mean()

    return get_activity_heartrate_mean


def get_activities_using_cache():
    print("get_activities_using_cache")
    from pathlib import Path
    client = get_client()
    list_activities = client.get_logged_in_athlete_activities(
        after='08-01-2022')
    existing_ids = list()

    parquet_file = Path("strava_activities.parquet")
    if parquet_file.is_file():
        activities_df = pd.read_parquet(parquet_file)
        existing_ids = activities_df['id'].values
    else:
        activities_df = pd.DataFrame()

    for act in list_activities:
        if str(act.id) not in existing_ids:
            act_dict = act.to_dict()
            act_dict["moving_time_minute"] = act_dict["moving_time"] / 60
            act_dict["distance_km"] = act_dict["distance"] / 1000
            act_dict["heartrate_mean"]  = get_activity_heartrate_mean(
                athlete_id=act.athlete.id, id=act.id)
                        
            if act_dict["heartrate_mean"]  != 0:
                act_dict["efficiency"]   =  act_dict["average_speed"]   / act_dict["heartrate_mean"]  * 1000              
            else:
                act_dict["efficiency"] = 0
            act_df = pd.json_normalize(act_dict)
            activities_df = pd.concat([activities_df, act_df])
            activities_df['id'] = activities_df['id'].apply(
                lambda x: x if pd.isnull(x) else str(int(x)))
            print("New activity " + str(act.id))
            
            activities_df.to_parquet(parquet_file)
    return activities_df


app = Dash(__name__)

df = get_activities_using_cache()
df['start_date_local']= pd.to_datetime(df['start_date_local'])
df_thisyear = df.loc[df.start_date_local  > pd.to_datetime('2022-01-06').tz_localize('utc'),['start_date_local',"distance_km","moving_time"]]
df_thisyear_week_summary = df_thisyear.groupby([df_thisyear['start_date_local'].dt.isocalendar().week]).agg({'distance_km': ['sum', 'max']})
df_thisyear_week_summary.columns = df_thisyear_week_summary.columns.droplevel()


time_distance_heartrate_graph_fig = px.scatter(df, x="moving_time_minute", y="distance_km", color="heartrate_mean", size="heartrate_mean")


thisyear_weekly_volume_graph_fig = px.bar(df_thisyear_week_summary, barmode = 'group')

thisyear_efficiency = df.loc[df["efficiency"] != 0]
thisyear_efficiency_vs_time_graph_fig = px.scatter(df.loc[df["efficiency"] != 0], x="start_date_local",y="efficiency",size="distance_km")
thisyear_efficiency_vs_distance_graph_fig = px.scatter(df.loc[df["efficiency"] != 0], x="distance_km",y="efficiency")

app.layout = html.Div(children=[
    html.H1(children='Stravache Analysis'),

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),

    dcc.Graph(
        id='time_distance_heartrate_graph',
        figure=time_distance_heartrate_graph_fig
    ),
    dcc.Graph(
        id='thisyear_weekly_volume_graph',
        figure=thisyear_weekly_volume_graph_fig
    ),
    dcc.Graph(
        id='thisyear_efficiency_vs_time_graph',
        figure=thisyear_efficiency_vs_time_graph_fig
    ),
    dcc.Graph(
        id='thisyear_efficiency_vs_distance_graph',
        figure=thisyear_efficiency_vs_distance_graph_fig
    )
])


if __name__ == '__main__':

    app.run_server(debug=True)
