__copyright__ = "Copyright 2015-2017 Contributing Entities"
__license__   = """
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import pandas

from .Logger import FastTripsLogger

class TCQSM:
    """
    Utility class for calculations based on the Transit Capacity and Quality of Service Manual (TCQSM)
    http://www.trb.org/Main/Blurbs/169437.aspx

    Used by the :py:class:`Trip` class to calculate dwell times for vehicles.
    """
    #: Column denoting number of channels. Integer.
    TCQSM_COL_NUM_CHANNELS               = "tcqsm_num_channels"
    #: Column denoting percent boards by channel. Float.  Exists for 1-6
    TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL  = "tcqsm_pct_boards_ch_%d"
    #: Column denoting percent alights by channel. Float.  Exists for 1-6
    TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL = "tcqsm_pct_alights_ch_%d"
    #: Column denoting channel boards. Float. Exists for 1-6
    TCQSM_COL_CHANNEL_BOARDS             = "tcqsm_boards_ch_%d"
    #: Column denoting channel alights. Float. Exists for 1-6
    TCQSM_COL_CHANNEL_ALIGHTS            = "tcqsm_alights_ch_%d"
    #: Column denoting channel board time in seconds. Float. Exists for 1-6
    TCQSM_COL_CHANNEL_BOARD_SEC          = "tcqsm_board_sec_ch_%d"
    #: Column denoting channel alight time in seconds. Float. Exists for 1-6
    TCQSM_COL_CHANNEL_ALIGHT_SEC         = "tcqsm_alight_sec_ch_%d"
    #: Column denoting channel flow time in seconds. Float. Exists for 1-6
    TCQSM_COL_CHANNEL_FLOW_SEC           = "tcqsm_flow_sec_ch_%d"
    #: Column denoting the TCQSM dwell time in seconds. Float.
    TCQSM_COL_DWELL_TIME_SEC             = "tcqsm_dwell_sec"

    #: todo: Make these overridable in config??

    #: Default number of channels if number_of_doors not specified
    TCQSM_DEFAULT_NUM_CHANNELS           = 3
    #: Default percent_using_farebox if not specificed
    TCQSM_DEFAULT_PERCENT_USING_FAREBOX  = 0.5
    #: Default fare_payment_method if not specified
    TCQSM_DEFAULT_FARE_PAYMENT_METHOD    = "smart_card"
    #: Default boarding_door if not specified
    TCQSM_DEFAULT_BOARDING_DOOR          = "front"
    #: Default boarding_height if not specified
    TCQSM_DEFAULT_BOARDING_HEIGHT        = "stairs"
    #: Default door_time if not specified
    TCQSM_DEFAULT_DOOR_TIME              = 2.5

    @staticmethod
    def calculate_boards_by_channel(trips_df):
        """
        Using the following columns:
        - :py:attr:`TCQSM.TCQSM_COL_NUM_CHANNELS`
        - :py:attr:`Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD`
        - :py:attr:`Trip.STOPTIMES_COLUMN_PERCENT_USING_FAREBOX`
        - :py:attr:`Trip.VEHICLES_COLUMN_BOARDING_DOOR`

        Sets the following columns:
        - :py:attr:`TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL` for channel [1,2,3,4,5,6]
        """
        from .Trip import Trip

        for channel_num in [1,2,3,4,5,6]:
            # initialize to zero
            trips_df[TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % channel_num] = 0.0

        ##-- Situation A: single-channel boarding w/ all fares paid or inspected upon boarding
        trips_df.loc[ trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS] == 1, TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 1] = 1.0

        ##-- Situation B: If need to have fare inspected or paid, assume double-channel boarding.
        ##  Channel 1 is for people who need to interact with farebox.
        ##  Channel 2 is for those who just need a visual inspection.
        trips_df.loc[ (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] != 1)& # 1channel covered in Situation A
                      (trips_df[Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD] != "none"),
            TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 1 ] = trips_df[Trip.STOPTIMES_COLUMN_PERCENT_USING_FAREBOX]
        trips_df.loc[ (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] != 1)& # 1channel covered in Situation A
                      (trips_df[Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD] != "none"),
            TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 2 ] = 1.0 - trips_df[Trip.STOPTIMES_COLUMN_PERCENT_USING_FAREBOX]

        ##-- Situation C: All door boarding, free or pre-paid fares

        # Based on Exhibit 6-58 and TCRP 299, a function of available door channels
        # NOTE: Derived from Exhibit 4-3 in TCQSM, 2nd Edition (5).
        # It can be assumed that boarding passengers are evenly divided among the remaining door channels. 
        PCT_BOARDS_USING_BUSIEST_CHANNEL = {
            2: 0.6,
            3: 0.45,
            4: 0.35,
            5: 0.3,
            6: 0.25,
        }

        # of the remaining, if front boarding door, based on farebox split
        trips_df.loc[ (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] != 1      )&  # 1channel covered in Situation A
                      (trips_df[Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD] == "none" )&  # non-none covered in Situation B
                      (trips_df[Trip.VEHICLES_COLUMN_BOARDING_DOOR      ] == "front"),
                      TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 1 ] = trips_df[Trip.STOPTIMES_COLUMN_PERCENT_USING_FAREBOX]
        trips_df.loc[ (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] != 1      )&
                      (trips_df[Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD] == "none" )&
                      (trips_df[Trip.VEHICLES_COLUMN_BOARDING_DOOR      ] == "front"),
                      TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 1 ] = 1.0 - trips_df[Trip.STOPTIMES_COLUMN_PERCENT_USING_FAREBOX]

        # if not front boarding door, first channel is based on above
        for ch in [2,3,4,5,6]:
            trips_df.loc[ (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] != 1      )&  # 1channel covered in Situation A
                          (trips_df[Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD] == "none" )&  # non-none covered in Situation B
                          (trips_df[Trip.VEHICLES_COLUMN_BOARDING_DOOR      ] != "front")&  # front boarding door covered above
                          (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] == ch),
                          TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 1] = PCT_BOARDS_USING_BUSIEST_CHANNEL[ ch ]

        # calculate remainder
        for ch in [2,3,4,5,6]:
            trips_df.loc[ (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] != 1      )&  # 1channel covered in Situation A
                          (trips_df[Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD] == "none" )&  # non-none covered in Situation B
                          (trips_df[Trip.VEHICLES_COLUMN_BOARDING_DOOR      ] != "front")&  # front boarding door covered above
                          (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] >= ch),
                          TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % ch] = (1.0 - trips_df[TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 1])/trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS]

        # verify they add up
        total_pct_boards_by_channel = trips_df[TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 1] + \
                                      trips_df[TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 2] + \
                                      trips_df[TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 3] + \
                                      trips_df[TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 4] + \
                                      trips_df[TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 5] + \
                                      trips_df[TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % 6]
        # FastTripsLogger.debug("total_pct_boards_by_channel=\n%s" % str(total_pct_boards_by_channel))
        assert(total_pct_boards_by_channel.min() == 1.0)
        assert(total_pct_boards_by_channel.max() == 1.0)

    @staticmethod
    def calculate_alights_by_channel(trips_df):
        """
        Using the following columns:
        - :py:attr:`TCQSM.TCQSM_COL_NUM_CHANNELS`
        - :py:attr:`Trip.VEHICLES_COLUMN_BOARDING_DOOR`

        Sets the following columns:
        - :py:attr:`TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL` for channel [1,2,3,4,5,6]
        """
        from .Trip import Trip

        for channel_num in [1,2,3,4,5,6]:
            # initialize to zero
            trips_df[TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % channel_num] = 0.0

        ##-- Situation A: single-channel
        trips_df.loc[ trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS] == 1, TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 1] = 1.0

        ##-- Situation B: single door
        # For now, num_channels = (num_doors-1)*2 + 1 so for num_doors=1, num_channels=1 so this is already covered
        # TODO: If num_channels is configurable (so not based on num_doors), then this should be updated for the following pseudocode
        # if num_doors == 1:
        #   pct_exits_by_channel[2] = 1.00

        # for now, put this in so 2channel is covered in some way
        trips_df.loc[ trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS] == 2, TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 2] = 1.0

        ##-- Situation C: two doors with all boardings thru front, assume 25% use front door and 75% rear door, split between channels
        # num_channels = (num_doors-1)*2 + 1 = (2-1)*2+1 = 3
        trips_df.loc[ (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS      ] == 3      )&
                      (trips_df[Trip.VEHICLES_COLUMN_BOARDING_DOOR] == "front"),
                      TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 2 ] = 0.25
        trips_df.loc[ (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS      ] == 3      )&
                      (trips_df[Trip.VEHICLES_COLUMN_BOARDING_DOOR] == "front"),
                      TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 3 ] = 0.75

        # TODO: If num_channels is configurable (so not based on num_doors), then this should be updated for the following pseudocode
        # pct_exits_by_channel[3] = 0.75 / (num_channels - 2)
        # if num_channels >= 4: pct_exits_by_channel[4] = 0.75 / (num_channels - 2)

        ##-- Situation D: two or more doors or all-door boarding

        PCT_ALIGHTS_USING_BUSIEST_CHANNEL = {
            2: 0.75,
            3: 0.45,
            4: 0.35,
            5: 0.30,
            6: 0.25,
        }

        # 3rd channel is based on above
        for ch in [2,3,4,5,6]:
            trips_df.loc[ (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS       ] > 2       )&  # 1channel covered in Situation A, 2channel not ok, see below
                          ((trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS      ] != 3      )|  # 3channel/front covered in Situation C
                           (trips_df[Trip.VEHICLES_COLUMN_BOARDING_DOOR] != "front"))&
                          (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS       ] == ch),
                          TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 3 ] = PCT_ALIGHTS_USING_BUSIEST_CHANNEL[ ch ]
        # if num_channels=2, we have {0, 0.25/0  0.75 } => error
        # if num_channels=3, we have {0, 0.55,   0.45, }
        # if num_channels=4, we have {0, 0.65/2, 0.35, 0.65/2 }
        # if num_channels=5, we have {0, 0.70/3, 0.30, 0.70/3,  0.70/3, }
        # if num_channels=6, we have {0, 0.75/4, 0.25, 0.75/4,  0.75/4,  0.75/4 }

        # remainder get the rest
        for ch in [2,4,5,6]:
            trips_df.loc[ (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] > 2       )&  # 1channel covered in Situation A, 2channel not ok, see below
                         ((trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] != 3      )|  # 3channel/front covered in Situation C
                          (trips_df[Trip.VEHICLES_COLUMN_BOARDING_DOOR      ] != "front"))&
                          (trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS            ] >= ch),
                          TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % ch] = (1.0 - trips_df[TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 3])/(trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS] - 2)

        # verify they add up
        total_pct_alights_by_channel = trips_df[TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 1] + \
                                       trips_df[TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 2] + \
                                       trips_df[TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 3] + \
                                       trips_df[TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 4] + \
                                       trips_df[TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 5] + \
                                       trips_df[TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % 6]
        # FastTripsLogger.debug("total_pct_alights_by_channel=\n%s" % str(total_pct_alights_by_channel))
        assert(total_pct_alights_by_channel.min() == 1.0)
        assert(total_pct_alights_by_channel.max() == 1.0)

    @staticmethod
    def calculate_board_alight_service_time(trips_df):
        """
        Using columns:
        - :py:attr:`Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD`
        - :py:attr:`Trip.SIM_COL_VEH_STANDEES`
        - :py:attr:`Trip.VEHICLES_COLUMN_BOARDING_HEIGHT`
        - :py:attr:`TCQSM.TCQSM_COL_NUM_CHANNELS`
        - :py:attr:`TCQSM.TCQSM_COL_CHANNEL_BOARDS`
        - :py:attr:`TCQSM.TCQSM_COL_CHANNEL_ALIGHTS`

        Sets columns:
        - :py:attr:`TCQSM.TCQSM_COL_CHANNEL_BOARD_SEC` for channels 1-6
        - :py:attr:`TCQSM.TCQSM_COL_CHANNEL_ALIGHT_SEC` for channels 1-6

        """
        from .Trip import Trip

        ############### BOARD ###############
        ## SOURCE: TCQSM 3rd edition Exhibit 6-4
        # Seconds per passenger
        AVG_BOARD_TIME_BY_FARE_METHOD = pandas.DataFrame.from_dict(data={
            'none'                : 1.75,
            'visual_inspection'   : 2.00,
            'single_ticket_token' : 3.00,
            'exact_change'        : 4.50,
            'ticket_validator'    : 4.00,
            'magstripe_card'      : 5.00,
            'smart_card'          : 2.75,
            }, orient='index').rename(columns={0:"_avg_board_time"})
        # print(AVG_BOARD_TIME_BY_FARE_METHOD)

        # create column, avg_board_time for this channel, by merging on payment_fare_method
        trips_df = pandas.merge(left       =trips_df,
                                right      =AVG_BOARD_TIME_BY_FARE_METHOD,
                                left_on    =Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD,
                                right_index=True)
        # print(trips_df["_avg_board_time"].value_counts())

        ## NOTE: Add 0.5 s/p to boarding times when standees are present.
        # if standees:                            avg_board_time += 0.5
        trips_df.loc[ trips_df[Trip.SIM_COL_VEH_STANDEES] > 0, "_avg_board_time" ] = trips_df["_avg_board_time"] + 0.5

        ##       Add 0.5 s/p for non-level boarding (1.0 s/p for motor coaches).
        # if boarding_height   == "stairs":       avg_board_time += 0.5
        # elif boarding_height == "steep stairs": avg_board_time += 1.0
        trips_df.loc[ trips_df[Trip.VEHICLES_COLUMN_BOARDING_HEIGHT] == "stairs",       "_avg_board_time" ] = trips_df["_avg_board_time"] + 0.5
        trips_df.loc[ trips_df[Trip.VEHICLES_COLUMN_BOARDING_HEIGHT] == "steep_stairs", "_avg_board_time" ] = trips_df["_avg_board_time"] + 1.0

        ############### ALIGHT ###############
        ## SOURCE: TCQSM 3rd edition Exhibit 6-4
        AVG_ALIGHT_TIME_BY_DOOR = pandas.DataFrame.from_dict(data={
            'front_door'    : 2.50,
            'rear_door'     : 1.75,
            }, orient='index').rename(columns={0:"_avg_alight_time"})
        # print(AVG_ALIGHT_TIME_BY_DOOR)

        # if channel >= 2: alight_door = 'rear_door'
        # else:            alight_door = 'front_door'
        trips_df["_alight_door"] = "front_door"
        trips_df.loc[trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS] >= 2, "_alight_door"] = "rear_door"

        # create column, avg_alight_time for this channel, by merging on _alight_door
        trips_df = pandas.merge(left       =trips_df,
                                right      =AVG_ALIGHT_TIME_BY_DOOR,
                                left_on    ="_alight_door",
                                right_index=True)
        # print(trips_df["_avg_alight_time"].value_counts())

        for channel_num in [1,2,3,4,5,6]:
            ## When more than 25% of the passenger flow through a single door channel is in the
            ## opposite direction of the main flow of passengers, increase both boarding and
            ## alighting service times by 20% to account for passenger congestion at the door

            # pct_boards = channel_boards/(channel_boards + channel_exits)
            # if min(pct_boards, pct_exits) > 0.25: avg_board_time = avg_board_time * 1.20
            trips_df["_pct_boards" ] = trips_df[TCQSM.TCQSM_COL_CHANNEL_BOARDS % channel_num] / (trips_df[TCQSM.TCQSM_COL_CHANNEL_BOARDS % channel_num] + trips_df[TCQSM.TCQSM_COL_CHANNEL_ALIGHTS % channel_num])
            trips_df["_pct_alights"] = 1.0 - trips_df["_pct_boards" ]

            trips_df.loc[ trips_df[["_pct_boards","_pct_alights"]].min(axis=1) > 0.25,  "_avg_board_time" ] = trips_df["_avg_board_time" ] * 1.20
            trips_df.loc[ trips_df[["_pct_boards","_pct_alights"]].min(axis=1) > 0.25,  "_avg_alight_time"] = trips_df["_avg_alight_time"] * 1.20

            # channel_board_time  = channel_boards  * avg_board_time
            # channel_alight_time = channel_alights * avg_alight_time
            trips_df[TCQSM.TCQSM_COL_CHANNEL_BOARD_SEC  % channel_num ] = trips_df[TCQSM.TCQSM_COL_CHANNEL_BOARDS  % channel_num] * trips_df["_avg_board_time" ]
            trips_df[TCQSM.TCQSM_COL_CHANNEL_ALIGHT_SEC % channel_num ] = trips_df[TCQSM.TCQSM_COL_CHANNEL_ALIGHTS % channel_num] * trips_df["_avg_alight_time"]

        # delete temp cols
        trips_df.drop(["_avg_board_time","_avg_alight_time","_alight_door","_pct_boards","_pct_alights"], axis=1, inplace=True)

        return trips_df

    @staticmethod
    def calculate_channel_flow_time(trips_df):
        """
        Using the following columns:
        - :py:attr:`TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL` for channel [1,2,3,4,5,6]
        - :py:attr:`TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL` for channel [1,2,3,4,5,6]
        - :py:attr:`Trip.SIM_COL_VEH_BOARDS`
        - :py:attr:`Trip.SIM_COL_VEH_ALIGHTS`

        Sets the following columns:
        - :py:attr:`TCQSM.TCQSM_COL_CHANNEL_FLOW_SEC` for channel [1,2,3,4,5,6]
        """
        from .Trip import Trip

        # calc channel boards, exits
        for ch in [1,2,3,4,5,6]:
            trips_df[TCQSM.TCQSM_COL_CHANNEL_BOARDS  % ch] = trips_df[Trip.SIM_COL_VEH_BOARDS ]*trips_df[TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL  % ch]
            trips_df[TCQSM.TCQSM_COL_CHANNEL_ALIGHTS % ch] = trips_df[Trip.SIM_COL_VEH_ALIGHTS]*trips_df[TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % ch]

        trips_df = TCQSM.calculate_board_alight_service_time(trips_df)
        FastTripsLogger.debug("calculate_channel_flow_time snap=\n%s" % trips_df.head())
        FastTripsLogger.debug("calculate_channel_flow_time dtypes=\n%s" % str(trips_df.dtypes))

        for ch in [1,2,3,4,5,6]:
            # return channel_board_time + channel_exit_time #note that it doesn't make sense to me that this is necessarily additive
            trips_df[TCQSM.TCQSM_COL_CHANNEL_FLOW_SEC % ch] = trips_df[TCQSM.TCQSM_COL_CHANNEL_BOARD_SEC % ch] + trips_df[TCQSM.TCQSM_COL_CHANNEL_ALIGHT_SEC % ch]

            # clean up intermediates
            trips_df.drop([TCQSM.TCQSM_COL_CHANNEL_BOARDS    % ch, TCQSM.TCQSM_COL_CHANNEL_ALIGHTS    % ch,
                           TCQSM.TCQSM_COL_CHANNEL_BOARD_SEC % ch, TCQSM.TCQSM_COL_CHANNEL_ALIGHT_SEC % ch], axis=1, inplace=True)
        return trips_df

    @staticmethod
    def calculate_tcqsm_dwell(trips_df):
        """
        For rows in trips_df where the TCQSM_CALC_DWELL_TF column is true, calculates the dwell time in seconds based on TCQSM guidelines.

        Variables from GTFS-plus
        - Trip.STOPTIMES_COLUMN_PERCENT_USING_FAREBOX
        - Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD
        - Trip.VEHICLES_COLUMN_BOARDING_HEIGHT
        - Trip.VEHICLES_COLUMN_DOOR_TIME
        - Trip.VEHICLES_COLUMN_BOARDING_DOOR
        - Trip.VEHICLES_COLUMN_NUMBER_OF_DOORS

        Variables from FT
        - Trip.SIM_COL_VEH_STANDEES
        - Trip.SIM_COL_VEH_BOARDS
        - Trip.SIM_COL_VEH_ALIGHTS
        """
        FastTripsLogger.debug("calculate_tcqsm_dwell() trips_df starts as\n%s" % str(trips_df.head()))

        trips_df_cols = list(trips_df.columns.values)

        from .Trip import Trip

        # set number of channels based on number of doors, if it's available.  Use default if not available.
        if Trip.VEHICLES_COLUMN_NUMBER_OF_DOORS in trips_df_cols:
            trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS] = (trips_df[Trip.VEHICLES_COLUMN_NUMBER_OF_DOORS]-1)*2 + 1
            # set na values to default
            trips_df.fillna(value={TCQSM.TCQSM_COL_NUM_CHANNELS:TCQSM.TCQSM_DEFAULT_NUM_CHANNELS}, inplace=True)
            # make sure it's in the range of [1,6]
            trips_df.loc[trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS] < 1, TCQSM.TCQSM_COL_NUM_CHANNELS ] = 1
            trips_df.loc[trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS] > 6, TCQSM.TCQSM_COL_NUM_CHANNELS ] = 6
        else:
            trips_df[TCQSM.TCQSM_COL_NUM_CHANNELS] = TCQSM.TCQSM_DEFAULT_NUM_CHANNELS

        # set the fare_payment_method if not available
        if Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD in trips_df_cols:
            trips_df.fillna(value={Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD:TCQSM.TCQSM_DEFAULT_FARE_PAYMENT_METHOD}, inplace=True)
        else:
            trips_df[Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD] = TCQSM.TCQSM_DEFAULT_FARE_PAYMENT_METHOD
        FastTripsLogger.debug("calculate_tcqsm_dwell() fare_payment_method value_counts:\n%s" % str(trips_df["fare_payment_method"].value_counts()))

        # set the percent_using_farebox if not available
        if Trip.STOPTIMES_COLUMN_PERCENT_USING_FAREBOX in trips_df_cols:
            trips_df.fillna(value={Trip.STOPTIMES_COLUMN_PERCENT_USING_FAREBOX:TCQSM.TCQSM_DEFAULT_PERCENT_USING_FAREBOX}, inplace=True)
        else:
            trips_df[Trip.STOPTIMES_COLUMN_PERCENT_USING_FAREBOX] = TCQSM.TCQSM_DEFAULT_PERCENT_USING_FAREBOX

        # set the boarding_door if not available
        if Trip.VEHICLES_COLUMN_BOARDING_DOOR in trips_df_cols:
            trips_df.fillna(value={Trip.VEHICLES_COLUMN_BOARDING_DOOR:TCQSM.TCQSM_DEFAULT_BOARDING_DOOR }, inplace=True)
        else:
            trips_df[Trip.VEHICLES_COLUMN_BOARDING_DOOR] = TCQSM.TCQSM_DEFAULT_BOARDING_DOOR

        # set the boarding_height if not available
        if Trip.VEHICLES_COLUMN_BOARDING_HEIGHT in trips_df_cols:
            trips_df.fillna(value={Trip.VEHICLES_COLUMN_BOARDING_HEIGHT:TCQSM.TCQSM_DEFAULT_BOARDING_HEIGHT }, inplace=True)
        else:
            trips_df[Trip.VEHICLES_COLUMN_BOARDING_HEIGHT] = TCQSM.TCQSM_DEFAULT_BOARDING_HEIGHT

        # set the door_time if not available
        if Trip.VEHICLES_COLUMN_DOOR_TIME in trips_df_cols:
            trips_df.fillna(value={Trip.VEHICLES_COLUMN_DOOR_TIME:TCQSM.TCQSM_DEFAULT_DOOR_TIME }, inplace=True)
        else:
            trips_df[Trip.VEHICLES_COLUMN_DOOR_TIME] = TCQSM.TCQSM_DEFAULT_DOOR_TIME

        # Requires columns
        # - TCQSM.TCQSM_COL_NUM_CHANNELS
        # - Trip.VEHICLES_COLUMN_FARE_PAYMENT_METHOD
        # - Trip.STOPTIMES_COLUMN_PERCENT_USING_FAREBOX
        # - Trip.VEHICLES_COLUMN_BOARDING_DOOR
        # Adds columns
        # - TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % [1,2,3,4,5,6]
        TCQSM.calculate_boards_by_channel(trips_df)
        FastTripsLogger.debug("calculate_tcqsm_dwell() trips_df after calculate_boards_by_channel()\n%s" % str(trips_df.head(10)))

        # Requires columns
        # - TCQSM.TCQSM_COL_NUM_CHANNELS
        # - Trip.VEHICLES_COLUMN_BOARDING_DOOR
        # Adds columns
        # - TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % [1,2,3,4,5,6]
        TCQSM.calculate_alights_by_channel(trips_df)
        FastTripsLogger.debug("calculate_tcqsm_dwell() trips_df after calculate_alights_by_channel()\n%s" % str(trips_df.head(10)))

        # Using the following columns:
        # - TCQSM.TCQSM_COL_PERCENT_BOARDS_BY_CHANNEL % [1,2,3,4,5,6]
        # - TCQSM.TCQSM_COL_PERCENT_ALIGHTS_BY_CHANNEL % [1,2,3,4,5,6]
        # - Trip.SIM_COL_VEH_BOARDS
        # - Trip.SIM_COL_VEH_ALIGHTS

        # Sets the following columns:
        # - TCQSM.TCQSM_COL_CHANNEL_FLOW_SEC % [1,2,3,4,5,6]
        trips_df = TCQSM.calculate_channel_flow_time(trips_df)

        # pax_flow_time = max(channel_flow_times)
        trips_df["_pax_flow_time"] = trips_df[[TCQSM.TCQSM_COL_CHANNEL_FLOW_SEC % 1,
                                               TCQSM.TCQSM_COL_CHANNEL_FLOW_SEC % 2,
                                               TCQSM.TCQSM_COL_CHANNEL_FLOW_SEC % 3,
                                               TCQSM.TCQSM_COL_CHANNEL_FLOW_SEC % 4,
                                               TCQSM.TCQSM_COL_CHANNEL_FLOW_SEC % 5,
                                               TCQSM.TCQSM_COL_CHANNEL_FLOW_SEC % 6]].max(axis=1)

        # Used to calculate efficiency loss from having multiple boarding areas.  Range is from 0 - 8 seconds for 1 - 5 boarding areas.
        # For FT, assume single boarding area, which results in zero lost time.
        trips_df["_boarding_lost_time"] = 0

        # get value from vehicle_ft, else use Fast-Trips default of 2.5 [just threw that out there ]
        # validate to be between 2-5 seconds
        # total_dwell = boarding_lost_time + door_open_close_time + pax_flow_time
        trips_df[TCQSM.TCQSM_COL_DWELL_TIME_SEC] = trips_df["_boarding_lost_time"] + trips_df[Trip.VEHICLES_COLUMN_DOOR_TIME] + trips_df["_pax_flow_time"]

        # return the original columns plus tcqsm_dwell if it wasn't there
        if TCQSM.TCQSM_COL_DWELL_TIME_SEC not in trips_df_cols:
            trips_df_cols.append(TCQSM.TCQSM_COL_DWELL_TIME_SEC)

        trips_df = trips_df[trips_df_cols]
        return trips_df