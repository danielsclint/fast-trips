import numpy
import pandas

from .Assignment import  Assignment
from .Passenger import Passenger
from .PathSet import PathSet
from .Trip import Trip


class Simulator:

    RANDOM_NUMBER_SEED = 1

    PF_COL_PATH_NUM = 'pathnum'

    PF_COL_PROBABILITY = 'pf_probability'

    SIM_COL_PAX_CHOSEN = 'path_picked'

    TRIP_LIST_COLUMN_PERSON_ID = 'person_id'

    TRIP_LIST_COLUMN_PERSON_TRIP_ID = 'person_trip_id'

    SIM_COL_RAND = 'rand'
    SIM_COL_CUMPROB = 'cumulative_prob'

    #: Chosen status for path
    SIM_COL_PAX_PATH_PICKED = 'path_picked'
    #: categories for SIM_COL_PAX_CHOSEN
    CHOSEN_NOT_CHOSEN_YET = "unchosen"
    CHOSEN_REJECTED = "rejected"
    #: These will be ordered, so to select chosen, choose those > CHOSEN_NOT_CHOSEN_YET
    CHOSEN_CATEGORIES = [CHOSEN_REJECTED, CHOSEN_NOT_CHOSEN_YET, SIM_COL_PAX_PATH_PICKED]

    @staticmethod
    def simulate(FT, output_dir, iteration, pathfinding_iteration, pathset_paths_df, pathset_links_df, veh_trips_df):

        #### Step 1: Select Path with Monte Carlo based on probabilities
        pathset_paths_df, pathset_links_df = Simulator.choose_paths(pathset_paths_df, pathset_links_df)

        #### Step 2: Put passengers on the transit vehicles and link boarding and alighting times for passengers
        passengers_df = pathset_links_df[pathset_links_df.chosen].copy()
        veh_trips_df = Simulator.load_passengers_on_vehicles(passengers_df, veh_trips_df)
        pathset_links_df = Simulator.set_passenger_times(pathset_links_df, veh_trips_df)

        #### Step 3: Bump passengers from overcapacity vehicles and remove transfer loadings if missed initial connection
        pathset_links_df = Simulator.bump_overcapacity(pathset_paths_df, pathset_links_df, veh_trips_df)

        #### Step 4: Put remaining passengers on the transit vehicles
        passengers_df = pathset_links_df[(pathset_links_df.chosen) & (pathset_links_df.board_state == 'boarded')].copy()
        veh_trips_df = Simulator.load_passengers_on_vehicles(passengers_df, veh_trips_df)

        #### Step 5: Update vehicle travel times and reset passenger boarding and alighting times
        veh_trips_df = Trip.update_trip_times(veh_trips_df, False)
        pathset_links_df = Simulator.set_passenger_times(pathset_links_df, veh_trips_df)

        #### Step 6: Remove missed transfers
        Simulator.boot_missed_transfers()

        while True:

            Simulator.update_veh_travel_times()

            Simulator.add_booted_passengers()

            Simulator.update_veh_travel_times()

            Simulator.boot_missed_transfers()

    @staticmethod
    def choose_paths(pathset_paths_df, pathset_links_df):
        numpy.random.seed(Simulator.RANDOM_NUMBER_SEED)

        trip_list_df = pathset_paths_df[
            [Simulator.TRIP_LIST_COLUMN_PERSON_ID, Simulator.TRIP_LIST_COLUMN_PERSON_TRIP_ID]].drop_duplicates()
        trip_list_df[Simulator.SIM_COL_RAND] = numpy.random.random(len(trip_list_df))

        pathset_paths_df = pandas.merge(pathset_paths_df,
                                        trip_list_df,
                                        on=[Simulator.TRIP_LIST_COLUMN_PERSON_ID,
                                            Simulator.TRIP_LIST_COLUMN_PERSON_TRIP_ID])

        pathset_paths_df[Simulator.SIM_COL_CUMPROB] = pathset_paths_df.groupby(
            [Simulator.TRIP_LIST_COLUMN_PERSON_ID, Simulator.TRIP_LIST_COLUMN_PERSON_TRIP_ID])[
            Simulator.PF_COL_PROBABILITY].cumsum()

        pathset_paths_df[Simulator.SIM_COL_PAX_CHOSEN] = False
        pathset_paths_df.loc[pathset_paths_df[Simulator.SIM_COL_RAND] < pathset_paths_df[Simulator.SIM_COL_CUMPROB],
                             Simulator.SIM_COL_PAX_PATH_PICKED] = True
        overs = pathset_paths_df.loc[pathset_paths_df[Simulator.SIM_COL_PAX_PATH_PICKED]]

        paths_picked = overs.loc[overs.groupby([Simulator.TRIP_LIST_COLUMN_PERSON_ID,
                                          Simulator.TRIP_LIST_COLUMN_PERSON_TRIP_ID])[Simulator.SIM_COL_CUMPROB].agg('idxmin')].index
        pathset_paths_df[Simulator.SIM_COL_PAX_PATH_PICKED] = False
        pathset_paths_df.loc[paths_picked, Simulator.SIM_COL_PAX_PATH_PICKED] = True

        pathset_paths_df.drop([Simulator.SIM_COL_RAND, Simulator.SIM_COL_CUMPROB], axis=1, inplace=True)

        if Simulator.SIM_COL_PAX_PATH_PICKED in list(pathset_links_df.columns.values):
            pathset_links_df.drop(Simulator.SIM_COL_PAX_PATH_PICKED, axis=1, inplace=True)

        pathset_links_df = pandas.merge(left=pathset_links_df,
                                        right=pathset_paths_df[[Simulator.TRIP_LIST_COLUMN_PERSON_ID,
                                                                Simulator.TRIP_LIST_COLUMN_PERSON_TRIP_ID,
                                                                Simulator.PF_COL_PATH_NUM,
                                                                Simulator.SIM_COL_PAX_PATH_PICKED]],
                                        how="left")

        pathset_links_df['chosen'] = numpy.nan
        pathset_links_df.loc[pathset_links_df[Simulator.SIM_COL_PAX_PATH_PICKED], 'chosen'] = Simulator.SIM_COL_PAX_PATH_PICKED

        return pathset_paths_df, pathset_links_df

    @staticmethod
    def load_passengers_on_vehicles(pathset_links_df, veh_trips_df):
        if Trip.SIM_COL_VEH_BOARDS in list(veh_trips_df.columns.values):
            veh_trips_df.drop([Trip.SIM_COL_VEH_BOARDS,
                               Trip.SIM_COL_VEH_ALIGHTS,
                               Trip.SIM_COL_VEH_ONBOARD], axis=1, inplace=True)

        if Trip.SIM_COL_VEH_OVERCAP in veh_trips_df:
            veh_trips_df[Trip.SIM_COL_VEH_OVERCAP] = numpy.nan
            veh_trips_df[Trip.SIM_COL_VEH_OVERCAP_FRAC] = numpy.nan

        veh_trips_df_len = len(veh_trips_df)

        passengers_df = Passenger.get_chosen_links(pathset_links_df)
        # only care about trips
        passengers_df = passengers_df.loc[passengers_df[Passenger.PF_COL_ROUTE_ID].notnull()]

        # Group to boards by counting trip_list_id_nums for a (trip_id, A_id as stop_id)
        passenger_trips_boards = passengers_df[
                [Passenger.TRIP_LIST_COLUMN_TRIP_LIST_ID_NUM, Trip.STOPTIMES_COLUMN_TRIP_ID_NUM, 'A_id_num', 'A_seq']
            ].groupby([Trip.STOPTIMES_COLUMN_TRIP_ID_NUM, 'A_id_num', 'A_seq']).count()

        passenger_trips_boards.index.names = [Trip.STOPTIMES_COLUMN_TRIP_ID_NUM,
                                              Trip.STOPTIMES_COLUMN_STOP_ID_NUM,
                                              Trip.STOPTIMES_COLUMN_STOP_SEQUENCE]

        # And alights by counting path_ids for a (trip_id, B_id as stop_id)
        passenger_trips_alights = passengers_df[
                [Passenger.TRIP_LIST_COLUMN_TRIP_LIST_ID_NUM, Trip.TRIPS_COLUMN_TRIP_ID_NUM, 'B_id_num', 'B_seq']
            ].groupby([Trip.TRIPS_COLUMN_TRIP_ID_NUM,'B_id_num','B_seq']).count()

        passenger_trips_alights.index.names = [Trip.STOPTIMES_COLUMN_TRIP_ID_NUM,
                                               Trip.STOPTIMES_COLUMN_STOP_ID_NUM,
                                               Trip.STOPTIMES_COLUMN_STOP_SEQUENCE]

        # Join them to the transit vehicle trips so we can put people on vehicles (boards)
        veh_loaded_df = pandas.merge(left        = veh_trips_df,
                                     right       = passenger_trips_boards,
                                     left_on     = [Trip.STOPTIMES_COLUMN_TRIP_ID_NUM,
                                                    Trip.STOPTIMES_COLUMN_STOP_ID_NUM,
                                                    Trip.STOPTIMES_COLUMN_STOP_SEQUENCE],
                                     right_index = True,
                                     how         = 'left')
        veh_loaded_df.rename(columns={Passenger.TRIP_LIST_COLUMN_TRIP_LIST_ID_NUM:Trip.SIM_COL_VEH_BOARDS}, inplace=True)


        # Join for alights
        veh_loaded_df = pandas.merge(left        = veh_loaded_df,
                                     right       = passenger_trips_alights,
                                    left_on      = [Trip.TRIPS_COLUMN_TRIP_ID_NUM,
                                                    Trip.STOPTIMES_COLUMN_STOP_ID_NUM,
                                                    Trip.STOPTIMES_COLUMN_STOP_SEQUENCE],
                                    right_index  = True,
                                    how          ='left')
        veh_loaded_df.rename(columns={Passenger.TRIP_LIST_COLUMN_TRIP_LIST_ID_NUM:Trip.SIM_COL_VEH_ALIGHTS}, inplace=True)
        veh_loaded_df.fillna(value=0, inplace=True)
        assert(len(veh_loaded_df)==veh_trips_df_len)

        # these are ints, not floats
        veh_loaded_df[[Trip.SIM_COL_VEH_BOARDS, Trip.SIM_COL_VEH_ALIGHTS]] = \
            veh_loaded_df[[Trip.SIM_COL_VEH_BOARDS, Trip.SIM_COL_VEH_ALIGHTS]].astype(int)

        veh_loaded_df.set_index([Trip.TRIPS_COLUMN_TRIP_ID_NUM,Trip.STOPTIMES_COLUMN_STOP_SEQUENCE],inplace=True)
        veh_loaded_df[Trip.SIM_COL_VEH_ONBOARD    ] = veh_loaded_df[Trip.SIM_COL_VEH_BOARDS    ] - veh_loaded_df[Trip.SIM_COL_VEH_ALIGHTS    ]

        # on board is the cumulative sum of boards - alights
        trips_cumsum = veh_loaded_df[[Trip.SIM_COL_VEH_ONBOARD]].groupby(level=[0]).cumsum()
        veh_loaded_df.drop([Trip.SIM_COL_VEH_ONBOARD], axis=1, inplace=True) # replace with cumsum
        veh_loaded_df = pandas.merge(left        = veh_loaded_df,
                                     right       = trips_cumsum,
                                     left_index  = True,
                                     right_index = True,
                                     how         = 'left')

        assert(len(veh_loaded_df)==veh_trips_df_len)
        # print veh_trips_df.loc[5123368]
        veh_loaded_df.reset_index(inplace=True)

        # overcap = how many people are problematic, or onboard-totalcap.  If negative, we have space.
        # overcap_frac = what percentage of boards are problematic
        veh_loaded_df[Trip.SIM_COL_VEH_OVERCAP     ] = veh_loaded_df[Trip.SIM_COL_VEH_ONBOARD] - veh_loaded_df[Trip.VEHICLES_COLUMN_TOTAL_CAPACITY]
        veh_loaded_df[Trip.SIM_COL_VEH_OVERCAP_FRAC] = 0.0
        veh_loaded_df.loc[veh_loaded_df[Trip.SIM_COL_VEH_BOARDS ]>0, Trip.SIM_COL_VEH_OVERCAP_FRAC] = veh_loaded_df[Trip.SIM_COL_VEH_OVERCAP]/veh_loaded_df[Trip.SIM_COL_VEH_BOARDS]

        return veh_loaded_df

    @staticmethod
    def set_passenger_times(pathset_links_df, veh_loaded_df):
        if Assignment.SIM_COL_PAX_A_TIME in pathset_links_df:
            pathset_links_df.drop([Assignment.SIM_COL_PAX_A_TIME, Assignment.SIM_COL_PAX_B_TIME], axis=1, inplace=True)

        pathset_links_df = Assignment.find_passenger_vehicle_times(pathset_links_df, veh_loaded_df)

        passengers = Passenger.get_chosen_links(pathset_links_df)

        passengers[Assignment.SIM_COL_PAX_A_TIME] = numpy.nan
        passengers[Assignment.SIM_COL_PAX_A_TIME] = pandas.to_datetime(
            passengers[Assignment.SIM_COL_PAX_A_TIME])
        passengers[Assignment.SIM_COL_PAX_B_TIME] = numpy.nan
        passengers[Assignment.SIM_COL_PAX_B_TIME] = pandas.to_datetime(
            passengers[Assignment.SIM_COL_PAX_B_TIME])

        passengers.loc[
            passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_ACCESS, Assignment.SIM_COL_PAX_A_TIME] = \
            passengers[Passenger.PF_COL_PAX_A_TIME]
        passengers.loc[
            passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_ACCESS, Assignment.SIM_COL_PAX_B_TIME] = \
            passengers[Passenger.PF_COL_PAX_B_TIME]

        passengers.loc[
            passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_TRIP, Assignment.SIM_COL_PAX_B_TIME] = \
            passengers[Assignment.SIM_COL_PAX_ALIGHT_TIME]

        passenger_plus = passengers.copy()
        passenger_plus['linknum'] = passenger_plus['linknum'] + 1

        passengers = pandas.merge(passengers,
                     passenger_plus[['person_id', 'person_trip_id', 'pathnum','linknum', Assignment.SIM_COL_PAX_ALIGHT_TIME]],
                     how='left',
                     on=['person_id', 'person_trip_id', 'pathnum','linknum'],
                     suffixes=('','_plus')
                     )

        passengers.loc[passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_EGRESS, Assignment.SIM_COL_PAX_A_TIME] = \
            passengers.loc[passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_EGRESS, '{}_plus'.format(Assignment.SIM_COL_PAX_ALIGHT_TIME)]

        passengers.loc[passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_TRANSFER, Assignment.SIM_COL_PAX_A_TIME] = \
            passengers.loc[passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_TRANSFER, '{}_plus'.format(Assignment.SIM_COL_PAX_ALIGHT_TIME)]

        passengers.loc[passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_EGRESS, Assignment.SIM_COL_PAX_B_TIME] = \
            passengers.loc[passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_EGRESS, Assignment.SIM_COL_PAX_A_TIME] + \
            passengers.loc[passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_EGRESS, 'pf_linktime']

        passengers.loc[
            passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_TRANSFER, Assignment.SIM_COL_PAX_B_TIME] = \
            passengers.loc[passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_TRANSFER, Assignment.SIM_COL_PAX_A_TIME] + \
            passengers.loc[passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_TRANSFER, 'pf_linktime']

        passenger_plus = passengers.copy()
        passenger_plus['linknum'] = passenger_plus['linknum'] + 1

        passengers = pandas.merge(passengers,
                                  passenger_plus[['person_id', 'person_trip_id', 'pathnum', 'linknum',
                                                  Assignment.SIM_COL_PAX_B_TIME]],
                                  how='left',
                                  on=['person_id', 'person_trip_id', 'pathnum', 'linknum'],
                                  suffixes=('', '_plus')
                                  )

        passengers.loc[
            passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_TRIP, Assignment.SIM_COL_PAX_A_TIME] = \
            passengers.loc[passengers[Passenger.PF_COL_LINK_MODE] == PathSet.STATE_MODE_TRIP, '{}_plus'.format(
                Assignment.SIM_COL_PAX_B_TIME)]


        pathset_links_df = pandas.merge(pathset_links_df,
                                        passengers[['person_id', 'person_trip_id', 'pathnum', 'linknum',
                                                    Assignment.SIM_COL_PAX_A_TIME, Assignment.SIM_COL_PAX_B_TIME]],
                                        how='left',
                                        on=['person_id', 'person_trip_id', 'pathnum', 'linknum'])

        return pathset_links_df


    @staticmethod
    def load_passengers_with_capacity(iteration, pathfinding_iteration, simulation_iteration,
                                      pathset_paths_df, pathset_links_df, veh_loaded_df):
        #def load_passengers_on_vehicles_with_cap(FT, iteration, pathfinding_iteration, simulation_iteration,
        #                                         trips, pathset_paths_df, pathset_links_df, veh_loaded_df):
        """
                Check if we have boards on over-capacity vehicles.  Mark them and mark the boards.

                If :py:attr:`Assignment.CAPACITY_CONSTRAINT`, then bump off overcapacity passengers.

                The process is:

                1) Look at which vehicle links are over capacity, adding columns named :py:attr:`Trip.SIM_COL_VEH_OVERCAP`
                   and py:attr:`Trip.SIM_COL_VEH_OVERCAP_FRAC` to *veh_loaded_df*

                2) Look at the stops where the first people board after we're at capacity (impossible boards) if any

                3) If :py:attr:`Assignment.BUMP_ONE_AT_A_TIME`, select the first such stop by arrival time
                   Otherwise, select the first such stop for each vehicle trip

                4) Join these stops to pathset_links_df, so pathset_links_df now has column Assignment.SIM_COL_PAX_OVERCAP_FRAC

                5) If not :py:attr:`Assignment.CAPACITY_CONSTRAINT`, return (and drop the column named :py:attr:`Trip.SIM_COL_VEH_OVERCAP` from veh_loaded_df)

                6) Figure out which passenger trips are actually getting bumped.  Some people can get on at these stops, but not all, so let the first
                   ones that arrive at the stop get on and filter to the ones we'll actually bump.  Update the column named :py:attr:`Assignmment.SIM_COL_PAX_BUMP_ITER`.
                   If non-null, this represents the iteration the passenger got bumped.

                Return (chosen_paths_bumped, pathset_paths_df, pathset_links_df, veh_loaded_df)
                """
        # these are the relevant vehicle columns
        vehicle_trip_debug_columns = [ \
            Trip.TRIPS_COLUMN_ROUTE_ID,
            Trip.TRIPS_COLUMN_TRIP_ID,
            Trip.STOPTIMES_COLUMN_STOP_SEQUENCE,
            Trip.STOPTIMES_COLUMN_STOP_ID,
            Trip.VEHICLES_COLUMN_TOTAL_CAPACITY,
            Trip.SIM_COL_VEH_BOARDS,
            Trip.SIM_COL_VEH_ALIGHTS,
            Trip.SIM_COL_VEH_ONBOARD,
            Trip.SIM_COL_VEH_OVERCAP,
            Trip.SIM_COL_VEH_OVERCAP_FRAC
        ]
        # these are the relevant pathset links colums
        pax_links_debug_columns = [ \
            Passenger.TRIP_LIST_COLUMN_PERSON_ID,
            Passenger.TRIP_LIST_COLUMN_PERSON_TRIP_ID,
            Passenger.TRIP_LIST_COLUMN_TRIP_LIST_ID_NUM,
            Passenger.PF_COL_PATH_NUM,
            Passenger.PF_COL_LINK_NUM,
            Passenger.PF_COL_ROUTE_ID,
            Passenger.PF_COL_TRIP_ID,
            Passenger.PF_COL_PAX_A_TIME,
            "A_id", "A_id_num", "A_seq",
            Assignment.SIM_COL_PAX_A_TIME,
            Assignment.SIM_COL_PAX_OVERCAP,
            Assignment.SIM_COL_PAX_OVERCAP_FRAC,
            Assignment.SIM_COL_PAX_BOARD_STATE,
            Assignment.SIM_COL_PAX_BUMP_ITER,
            Assignment.SIM_COL_PAX_CHOSEN,
        ]

        current_pf_iter = 0.01 * pathfinding_iteration + iteration
        current_sim_iter = "iter%.2f sim%d" % (current_pf_iter, simulation_iteration)

        # this will involve looping
        # no one is bumped yet
        bump_iter = 0
        pathset_links_df[Assignment.SIM_COL_PAX_OVERCAP_FRAC] = numpy.NaN

        #if simulation_iteration == 0:
            # For those we just found paths for, no one is bumped or going on overcap vehicles yet
            # pathset_paths_df.loc[pathset_paths_df[Passenger.PF_COL_PF_ITERATION]==current_pf_iter, Assignment.SIM_COL_PAX_BUMP_ITER   ] = numpy.NaN
            # pathset_links_df.loc[pathset_links_df[Passenger.PF_COL_PF_ITERATION]==current_pf_iter, Assignment.SIM_COL_PAX_BUMP_ITER   ] = numpy.NaN
            # pathset_links_df.loc[pathset_links_df[Passenger.PF_COL_PF_ITERATION]==current_pf_iter, Assignment.SIM_COL_PAX_BOARD_STATE ] = numpy.NaN

        # anyone can be bumped, including those from previous pathfinding iters.  Otherwise, we wouldn't be able to ride to an earlier stop and bump them
        pathset_paths_df[Assignment.SIM_COL_PAX_BUMP_ITER] = numpy.NaN
        pathset_links_df[Assignment.SIM_COL_PAX_BUMP_ITER] = numpy.NaN
        pathset_links_df[Assignment.SIM_COL_PAX_BOARD_STATE] = numpy.NaN

        # make sure BOARD_STATE and CHOSEN are categorical
        pathset_paths_df[Assignment.SIM_COL_PAX_CHOSEN] = pandas.Categorical(
            pathset_paths_df[Assignment.SIM_COL_PAX_CHOSEN], categories=Assignment.CHOSEN_CATEGORIES, ordered=True)
        pathset_links_df[Assignment.SIM_COL_PAX_CHOSEN] = pandas.Categorical(
            pathset_links_df[Assignment.SIM_COL_PAX_CHOSEN], categories=Assignment.CHOSEN_CATEGORIES, ordered=True)
        pathset_links_df[Assignment.SIM_COL_PAX_BOARD_STATE] = pandas.Categorical(
            pathset_links_df[Assignment.SIM_COL_PAX_BOARD_STATE], categories=Assignment.BOARD_STATE_CATEGORICAL)

        while True:  # loop for capacity constraint

            #FastTripsLogger.info("  Step 5.1 Put passengers on transit vehicles.")
            # Put passengers on vehicles, updating the vehicle's boards, alights, onboard, overcap, overcap_frac
            veh_loaded_df = Assignment.put_passengers_on_vehicles(pathset_links_df, veh_loaded_df)
            #FastTripsLogger.debug("after putting passengers on vehicles, veh_loaded_df with onboard.head(30) = \n%s" %
            #                      veh_loaded_df.loc[
            #                          veh_loaded_df[Trip.SIM_COL_VEH_ONBOARD] > 0, vehicle_trip_debug_columns].head(
            #                          30).to_string())

            #if not Assignment.CAPACITY_CONSTRAINT:
            #    # We can't do anything about capacity so assume everyone boarded
            #    pathset_links_df.loc[(pathset_links_df[Passenger.PF_COL_PF_ITERATION] == current_pf_iter) &
            #                         (pathset_links_df[Passenger.PF_COL_TRIP_ID].notnull()),
            #                         Assignment.SIM_COL_PAX_BOARD_STATE] = "board_easy"
            #    break

            #FastTripsLogger.info("  Step 5.2 Capacity constraints on transit vehicles.")
            #if bump_iter == 0:
            #    FastTripsLogger.info(
            #        "          Bumping one at a time? %s" % ("true" if Assignment.BUMP_ONE_AT_A_TIME else "false"))

            # This will update board time, alight time, overcap, overcap_frac
            pathset_links_df = Simulator.set_passenger_times(pathset_links_df, veh_loaded_df)
            #pathset_links_df = Assignment.find_passenger_vehicle_times(pathset_links_df, veh_loaded_df)
            #FastTripsLogger.debug(
            #    "pathset_links_df.head(20)=\n%s" % pathset_links_df[pax_links_debug_columns].head(20).to_string())

            # make sure BOARD_STATE and CHOSEN are categorical
            pathset_links_df[Assignment.SIM_COL_PAX_CHOSEN] = pandas.Categorical(
                pathset_links_df[Assignment.SIM_COL_PAX_CHOSEN], categories=Assignment.CHOSEN_CATEGORIES, ordered=True)
            pathset_links_df[Assignment.SIM_COL_PAX_BOARD_STATE] = pandas.Categorical(
                pathset_links_df[Assignment.SIM_COL_PAX_BOARD_STATE], categories=Assignment.BOARD_STATE_CATEGORICAL)

            # CHOSEN: Everyone who can board easily, do so
            pathset_links_df.loc[pathset_links_df[Passenger.PF_COL_ROUTE_ID].notnull() &  # trip links only
                                 pathset_links_df[Assignment.SIM_COL_PAX_BUMP_ITER].isnull() &  # not already bumped
                                 (pathset_links_df[
                                      Assignment.SIM_COL_PAX_CHOSEN] > Assignment.CHOSEN_NOT_CHOSEN_YET) &  # chosen
                                 (pathset_links_df[Assignment.SIM_COL_PAX_OVERCAP] < 0),  # can board
                                 Assignment.SIM_COL_PAX_BOARD_STATE] = "board_easy"
            # CHOSEN:  Everyone who can squeeze in, do so
            pathset_links_df.loc[pathset_links_df[Passenger.PF_COL_ROUTE_ID].notnull() &  # trip links only
                                 pathset_links_df[Assignment.SIM_COL_PAX_BUMP_ITER].isnull() &  # not already bumped
                                 (pathset_links_df[
                                      Assignment.SIM_COL_PAX_CHOSEN] > Assignment.CHOSEN_NOT_CHOSEN_YET) &  # chosen
                                 (pathset_links_df[Assignment.SIM_COL_PAX_OVERCAP] == 0),  # can barely board
                                 Assignment.SIM_COL_PAX_BOARD_STATE] = "boarded"
            # UNCHOSEN: paths that are overcap -- nope
            pathset_links_df.loc[pathset_links_df[Passenger.PF_COL_ROUTE_ID].notnull() &  # trip links only
                                 pathset_links_df[Assignment.SIM_COL_PAX_BUMP_ITER].isnull() &  # not already bumped
                                 (pathset_links_df[
                                      Assignment.SIM_COL_PAX_CHOSEN] == Assignment.CHOSEN_NOT_CHOSEN_YET) &  # unchosen
                                 (pathset_links_df[Assignment.SIM_COL_PAX_OVERCAP] >= 0),  # overcap
                                 Assignment.SIM_COL_PAX_BOARD_STATE] = "bumped_unchosen"
            pathset_links_df.loc[pathset_links_df[Passenger.PF_COL_ROUTE_ID].notnull() &  # trip links only
                                 pathset_links_df[Assignment.SIM_COL_PAX_BUMP_ITER].isnull() &  # not already bumped
                                 (pathset_links_df[
                                      Assignment.SIM_COL_PAX_CHOSEN] == Assignment.CHOSEN_NOT_CHOSEN_YET) &  # unchosen
                                 (pathset_links_df[Assignment.SIM_COL_PAX_OVERCAP] >= 0),  # overcap
                                 Assignment.SIM_COL_PAX_BUMP_ITER] = bump_iter

            # For those trying to board overcap, choose the winners and losers
            # These are trips/stops over capacity
            overcap_df = veh_loaded_df.loc[veh_loaded_df[Trip.SIM_COL_VEH_OVERCAP] > 0]
            #FastTripsLogger.debug(
            #    "load_passengers_on_vehicles_with_cap() %d vehicle trip/stops over capacity: (showing head)\n%s" % \
            #    (len(overcap_df), overcap_df[vehicle_trip_debug_columns].head().to_string()))

            # If none, we're done
            if len(overcap_df) == 0:
                #FastTripsLogger.info("          No over-capacity vehicles")
                break

            # 2) Look at the trip-stops where the *first people* board after we're at capacity (impossible boards) if any
            bump_stops_df = overcap_df.groupby([Trip.STOPTIMES_COLUMN_TRIP_ID]).aggregate('first').reset_index()
            #FastTripsLogger.debug(
            #    "load_passengers_on_vehicles_with_cap() bump_stops_df iter=%d pf_iter=%d sim_iter=%d bump_iter=%d (%d rows, showing head):\n%s" %
            #    (iteration, pathfinding_iteration, simulation_iteration, bump_iter,
            #     len(bump_stops_df), bump_stops_df[vehicle_trip_debug_columns].head().to_string()))

            if Assignment.BUMP_ONE_AT_A_TIME:
                bump_stops_df.sort_values(by=[Trip.STOPTIMES_COLUMN_ARRIVAL_TIME], inplace=True)
                bump_stops_df = bump_stops_df.iloc[:1]

            #FastTripsLogger.info("          Need to bump %d passengers from %d trip-stops" % (
            #    bump_stops_df.overcap.sum(), len(bump_stops_df)))
            # debug -- see the whole trip
            #if True:
            #    FastTripsLogger.debug("load_passengers_on_vehicles_with_cap() Trips with bump stops:\n%s\n" % \
            #                          pandas.merge(
            #                              left=veh_loaded_df[vehicle_trip_debug_columns],
            #                              right=bump_stops_df[[Trip.STOPTIMES_COLUMN_TRIP_ID]],
            #                              how='inner').to_string())

            # make sure CHOSEN is categorical
            pathset_links_df[Assignment.SIM_COL_PAX_CHOSEN] = pandas.Categorical(
                pathset_links_df[Assignment.SIM_COL_PAX_CHOSEN], categories=Assignment.CHOSEN_CATEGORIES, ordered=True)

            # join CHOSEN pathset links to bump_stops_df; now passenger links boarding at a bump stop will have Trip.STOPTIMES_COLUMN_STOP_SEQUENCE set
            bumpstop_boards = pandas.merge(
                left=pathset_links_df.loc[pathset_links_df[Passenger.PF_COL_ROUTE_ID].notnull() &  # trip links only
                                          pathset_links_df[
                                              Assignment.SIM_COL_PAX_BUMP_ITER].isnull() &  # not already bumped
                                          (pathset_links_df[
                                               Assignment.SIM_COL_PAX_CHOSEN] > Assignment.CHOSEN_NOT_CHOSEN_YET)],
                # chosen
                left_on=[Trip.STOPTIMES_COLUMN_TRIP_ID, "A_seq"],
                right=bump_stops_df[[Trip.STOPTIMES_COLUMN_TRIP_ID, Trip.STOPTIMES_COLUMN_STOP_SEQUENCE]],
                right_on=[Trip.STOPTIMES_COLUMN_TRIP_ID, Trip.STOPTIMES_COLUMN_STOP_SEQUENCE],
                how="left")
            # bump candidates: boarding at bump stops, chosen paths
            bumpstop_boards = bumpstop_boards.loc[
                bumpstop_boards[Trip.STOPTIMES_COLUMN_STOP_SEQUENCE].notnull(),  # board at bump_stops_df stop
                pax_links_debug_columns].copy()

            # bump off later arrivals, later trip_list_num
            bumpstop_boards.sort_values(by=[ \
                Assignment.SIM_COL_PAX_A_TIME,  # I think this is correct
                Trip.STOPTIMES_COLUMN_TRIP_ID,
                "A_seq",
                Passenger.PF_COL_PAX_A_TIME,
                Passenger.TRIP_LIST_COLUMN_TRIP_LIST_ID_NUM],
                ascending=[True, True, True, False, False], inplace=True)
            bumpstop_boards.reset_index(drop=True, inplace=True)

            # For each trip_id, stop_seq, stop_id, we want the first *overcap* rows
            # group to trip_id, stop_seq, stop_id and count off
            bpb_count = bumpstop_boards.groupby([Trip.STOPTIMES_COLUMN_TRIP_ID, "A_seq", "A_id_num"]).cumcount()
            bpb_count.name = 'bump_index'
            # Add the bump index to our passenger-paths/stops
            bumpstop_boards = pandas.concat([bumpstop_boards, bpb_count], axis=1)

            # bump or board them
            bumpstop_boards[Assignment.SIM_COL_PAX_BOARD_STATE] = pandas.Categorical(["boarded"] * len(bumpstop_boards),
                                                                                     categories=Assignment.BOARD_STATE_CATEGORICAL)
            bumpstop_boards.loc[bumpstop_boards["bump_index"] < bumpstop_boards[
                Trip.SIM_COL_VEH_OVERCAP], Assignment.SIM_COL_PAX_BOARD_STATE] = "bumped"  # these folks got bumped
            bumpstop_boards.loc[bumpstop_boards["bump_index"] < bumpstop_boards[
                Trip.SIM_COL_VEH_OVERCAP], Assignment.SIM_COL_PAX_BUMP_ITER] = bump_iter  # these folks got bumped

            #FastTripsLogger.debug(
            #    "load_passengers_on_vehicles_with_cap() bumpstop_boards (%d rows, showing head):\n%s" % \
            #    (len(bumpstop_boards), bumpstop_boards.head(50).to_string()))

            # filter to unique passengers/paths who got bumped
            bump_paths = bumpstop_boards.loc[bumpstop_boards[Assignment.SIM_COL_PAX_BOARD_STATE] == "bumped",
                                             [Passenger.TRIP_LIST_COLUMN_PERSON_ID,
                                              Passenger.TRIP_LIST_COLUMN_TRIP_LIST_ID_NUM,
                                              Passenger.PF_COL_PATH_NUM]].drop_duplicates()
            chosen_paths_bumped = len(bump_paths)

            # figure when the wait time starts for the bump stops
            #new_bump_wait = bumpstop_boards[
            #    [Trip.STOPTIMES_COLUMN_TRIP_ID, "A_seq", "A_id_num", Passenger.PF_COL_PAX_A_TIME]].groupby( \
            #    [Trip.STOPTIMES_COLUMN_TRIP_ID, "A_seq", "A_id_num"]).first().reset_index(drop=False)
            #new_bump_wait.rename(columns={"A_seq": Trip.STOPTIMES_COLUMN_STOP_SEQUENCE,
            #                              "A_id_num": Trip.STOPTIMES_COLUMN_STOP_ID_NUM}, inplace=True)
            # need trip id num
            #new_bump_wait = trips.add_numeric_trip_id(new_bump_wait, Trip.STOPTIMES_COLUMN_TRIP_ID,
            #                                          Trip.STOPTIMES_COLUMN_TRIP_ID_NUM)
            #FastTripsLogger.debug(
            #    "new_bump_wait (%d rows, showing head):\n%s" % (len(new_bump_wait), new_bump_wait.head().to_string()))

            # incorporate it into the bump wait df
            #if type(Assignment.bump_wait_df) == type(None):
            #    Assignment.bump_wait_df = new_bump_wait
            #else:
            #    Assignment.bump_wait_df = pandas.concat([Assignment.bump_wait_df, new_bump_wait], axis=0)

            #    FastTripsLogger.debug(
            #        "load_passengers_on_vehicles_with_cap() bump_wait_df (%d rows, showing head):\n%s" %
            #        (len(Assignment.bump_wait_df), Assignment.bump_wait_df.head().to_string()))

            #    Assignment.bump_wait_df.drop_duplicates(subset=[Trip.STOPTIMES_COLUMN_TRIP_ID_NUM,
            #                                                    Trip.STOPTIMES_COLUMN_STOP_SEQUENCE], inplace=True)

            # finally, incorporate the board state and bump_iter to the full pathset_links_df
            pathset_links_df = pandas.merge(left=pathset_links_df,
                                            right=bumpstop_boards[[Passenger.TRIP_LIST_COLUMN_PERSON_ID,
                                                                   Passenger.TRIP_LIST_COLUMN_PERSON_TRIP_ID,
                                                                   Passenger.PF_COL_PATH_NUM,
                                                                   Passenger.PF_COL_LINK_NUM,
                                                                   Assignment.SIM_COL_PAX_BOARD_STATE,
                                                                   Assignment.SIM_COL_PAX_BUMP_ITER]],
                                            on=[Passenger.TRIP_LIST_COLUMN_PERSON_ID,
                                                Passenger.TRIP_LIST_COLUMN_PERSON_TRIP_ID,
                                                Passenger.PF_COL_PATH_NUM,
                                                Passenger.PF_COL_LINK_NUM],
                                            how="left",
                                            suffixes=["", " bb"],
                                            indicator=True)
            pathset_links_df.loc[pathset_links_df["_merge"] == "both", Assignment.SIM_COL_PAX_BOARD_STATE] = \
            pathset_links_df["%s bb" % Assignment.SIM_COL_PAX_BOARD_STATE]
            pathset_links_df.loc[pathset_links_df["_merge"] == "both", Assignment.SIM_COL_PAX_BUMP_ITER] = \
            pathset_links_df["%s bb" % Assignment.SIM_COL_PAX_BUMP_ITER]
            pathset_links_df.drop(
                ["_merge", "%s bb" % Assignment.SIM_COL_PAX_BOARD_STATE, "%s bb" % Assignment.SIM_COL_PAX_BUMP_ITER],
                axis=1, inplace=True)
            #FastTripsLogger.debug(pathset_links_df[pax_links_debug_columns].head())

            # bump the whole path
            bump_paths_df = pathset_links_df.loc[pathset_links_df[Assignment.SIM_COL_PAX_BUMP_ITER] == bump_iter,
                                                 [Passenger.TRIP_LIST_COLUMN_PERSON_ID,
                                                  Passenger.TRIP_LIST_COLUMN_PERSON_TRIP_ID,
                                                  Passenger.PF_COL_PATH_NUM]].drop_duplicates()
            pathset_paths_df = pandas.merge(left=pathset_paths_df,
                                            right=bump_paths_df,
                                            how="left",
                                            indicator=True)
            pathset_paths_df.loc[pathset_paths_df["_merge"] == "both", Assignment.SIM_COL_PAX_BUMP_ITER] = bump_iter
            pathset_paths_df.drop(["_merge"], axis=1, inplace=True)

            # communicate back to other links in the same path too
            pathset_links_df = pandas.merge(left=pathset_links_df,
                                            right=bump_paths_df,
                                            how="left",
                                            indicator=True)
            pathset_links_df.loc[pathset_links_df["_merge"] == "both", Assignment.SIM_COL_PAX_BUMP_ITER] = bump_iter
            pathset_links_df.loc[(pathset_links_df["_merge"] == "both") &
                                 (pathset_links_df[Assignment.SIM_COL_PAX_BOARD_STATE].isnull() |
                                  (pathset_links_df[Assignment.SIM_COL_PAX_BOARD_STATE] == "boarded") |
                                  (pathset_links_df[Assignment.SIM_COL_PAX_BOARD_STATE] == "board_easy")) &
                                 pathset_links_df[Passenger.PF_COL_ROUTE_ID].notnull(),
                                 Assignment.SIM_COL_PAX_BOARD_STATE] = "bumped_othertrip"
            pathset_links_df.drop(["_merge"], axis=1, inplace=True)

            #FastTripsLogger.info(
            #    "        -> completed loop bump_iter %d and bumped %d chosen paths" % (bump_iter, chosen_paths_bumped))

            if chosen_paths_bumped == 0:
                break

            bump_iter += 1

        if type(Assignment.bump_wait_df) == pandas.DataFrame and len(Assignment.bump_wait_df) > 0:
            Assignment.bump_wait_df[Passenger.PF_COL_PAX_A_TIME_MIN] = \
                Assignment.bump_wait_df[Passenger.PF_COL_PAX_A_TIME].map(
                    lambda x: (60.0 * x.hour) + x.minute + (x.second / 60.0))

        #if type(Assignment.bump_wait_df) == pandas.DataFrame and len(Assignment.bump_wait_df) > 0:
        #    FastTripsLogger.debug("Bump_wait_df:\n%s" % Assignment.bump_wait_df.to_string())

        return pathset_paths_df, pathset_links_df, veh_loaded_df

    @staticmethod
    def update_veh_travel_time():
        pass

    @staticmethod
    def boot_missed_transfers():
        pass

    @staticmethod
    def add_booted_passengers():
        pass