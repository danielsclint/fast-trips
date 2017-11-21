import pandas
from fasttrips import Assignment
from fasttrips import Passenger
from fasttrips import Simulator
from fasttrips import Trip

def test_choose_paths():
    pathset_paths_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\pathset_paths_sim.csv')
    pathset_links_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\pathset_links_sim.csv',
        parse_dates=['pf_A_time', 'pf_B_time', 'pf_linktime'], infer_datetime_format=True)
    pathset_links_df['pf_linktime'] = pandas.to_timedelta(pathset_links_df['pf_linktime'], 'm')
    pathset_links_df['pf_waittime'] = pandas.to_timedelta(pathset_links_df['pf_waittime'], 'm')
    veh_trips_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\veh_trips_sim.csv',
        parse_dates=['arrival_time', 'departure_time', 'trip_departure_time'], infer_datetime_format=True
    )
    veh_trips_df['original_travel_time'] = pandas.to_timedelta(veh_trips_df['original_travel_time'], 'm')
    veh_trips_df['travel_time'] = pandas.to_timedelta(veh_trips_df['travel_time'], 'm')

    pathset_paths_df, pathset_links_df = Simulator.choose_paths(pathset_paths_df, pathset_links_df)
    print 'end'

def test_load_passengers_on_vehicles():
    pathset_paths_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\pathset_paths_sim.csv')
    pathset_links_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\pathset_links_sim.csv',
        parse_dates=['pf_A_time', 'pf_B_time', 'pf_linktime'], infer_datetime_format=True)
    pathset_links_df['pf_linktime'] = pandas.to_timedelta(pathset_links_df['pf_linktime'], 'm')
    pathset_links_df['pf_waittime'] = pandas.to_timedelta(pathset_links_df['pf_waittime'], 'm')
    veh_trips_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\veh_trips_sim.csv',
        parse_dates=['arrival_time', 'departure_time', 'trip_departure_time'], infer_datetime_format=True
    )
    veh_trips_df['original_travel_time'] = pandas.to_timedelta(veh_trips_df['original_travel_time'], 'm')
    veh_trips_df['travel_time'] = pandas.to_timedelta(veh_trips_df['travel_time'], 'm')
    pathset_paths_df, pathset_links_df = Simulator.choose_paths(pathset_paths_df, pathset_links_df)
    passengers_df = pathset_links_df[pathset_links_df.chosen].copy()
    Simulator.load_passengers_on_vehicles(passengers_df, veh_trips_df)

def test_set_passenger_times():
    pathset_paths_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\pathset_paths_sim.csv')
    pathset_links_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\pathset_links_sim.csv',
        parse_dates=['pf_A_time', 'pf_B_time', 'pf_linktime'], infer_datetime_format=True)
    pathset_links_df['pf_linktime'] = pandas.to_timedelta(pathset_links_df['pf_linktime'], 'm')
    pathset_links_df['pf_waittime'] = pandas.to_timedelta(pathset_links_df['pf_waittime'], 'm')
    veh_trips_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\veh_trips_sim.csv',
        parse_dates=['arrival_time', 'departure_time', 'trip_departure_time'], infer_datetime_format=True
    )
    veh_trips_df['original_travel_time'] = pandas.to_timedelta(veh_trips_df['original_travel_time'], 'm')
    veh_trips_df['travel_time'] = pandas.to_timedelta(veh_trips_df['travel_time'], 'm')

    pathset_paths_df, pathset_links_df = Simulator.choose_paths(pathset_paths_df, pathset_links_df)
    passengers_df = pathset_links_df[pathset_links_df.chosen].copy()
    veh_trips_df = Simulator.load_passengers_on_vehicles(passengers_df, veh_trips_df)
    Simulator.set_passenger_times(pathset_links_df, veh_trips_df)

def test_bump_overcapacity():
    pathset_paths_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\pathset_paths_sim.csv')
    pathset_links_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\pathset_links_sim.csv',
        parse_dates=['pf_A_time', 'pf_B_time', 'pf_linktime'], infer_datetime_format=True)
    pathset_links_df['pf_linktime'] = pandas.to_timedelta(pathset_links_df['pf_linktime'], 'm')
    pathset_links_df['pf_waittime'] = pandas.to_timedelta(pathset_links_df['pf_waittime'], 'm')
    veh_trips_df = pandas.read_csv(
        r'C:\apps\fast-trips\fasttrips\Examples\test_scenario\output\example_converge\veh_trips_sim.csv',
        parse_dates=['arrival_time', 'departure_time', 'trip_departure_time'], infer_datetime_format=True
    )
    veh_trips_df['original_travel_time'] = pandas.to_timedelta(veh_trips_df['original_travel_time'], 'm')
    veh_trips_df['travel_time'] = pandas.to_timedelta(veh_trips_df['travel_time'], 'm')

    pathset_paths_df['sim_cost'] = pathset_paths_df['pf_cost']
    pathset_paths_df['probability'] = pathset_paths_df['pf_probability']
    num_passengers_arrived, num_chosen, pathset_paths_df, pathset_links_df = \
        Passenger.choose_paths(True, 1, 1, 1, pathset_paths_df, pathset_links_df)
    pathset_paths_df, pathset_links_df, veh_trips_df = Simulator.load_passengers_with_capacity(
        1, 1, 1, pathset_paths_df, pathset_links_df, veh_trips_df)



    pathset_links_df = Simulator.set_passenger_times(pathset_links_df, veh_trips_df)

    veh_trips_df = Trip.update_trip_times(veh_trips_df.copy(), False)
    pathset_links_df = Simulator.set_passenger_times(pathset_links_df, veh_trips_df)
    pathset_links_df = Assignment.set_alight_delay()
    pathset_paths_df, pathset_links_df = Assignment.flag_missed_transfers(pathset_paths_df, pathset_links_df)
    print veh_trips_df


