
from project47.routing import *
import numpy as np
from copy import copy
import json
import os

def sim(s:RoutingSolution, update_function, seed:int=0):
    """ Simple simulator

    TODO: Docs need a rewrite

    The current behaviour is to have each vehicle travel along each route individually. Times, distances,
    and the futile deliveries are calculated and recorded according to the provided functions.

    Vehicles are all assumed to leave at time 0, and travel without breaks.

    The behaviour can be altered somewhat by providing a policy function, which alters the solution according to
    the current state. This is somewhat experimental, and not all policies can be captured with this. But,
    a fair few may be; need to experiment with them more.
    On a related topic, I wonder if there would be any benefit to using a discrete event simulation library here?

    Parameters
    ----------
    s : RoutingSolution
        The solution for a single day for the routes each vehicle travels
    distance_function : function
        Given the location numbers and the current time, calculate the distance to travel
        between them.
    time_function : function
        Given the location numbers and the current time, calculate the time to travel
        between them.
    futile_function : function
        Given the location numbers and the current time, calculate whether the next delivery will be futile.
        This is a bit weird, it doesn't really fit in the same framework as distance and time.
    policies : list
        A list of functions to execute on the current solution each time we travel between locations.
    seed : int
        The random seed. Defaults to 0 for reproducibility. We should try to stick with numpy random functions
        throughout our code to assist with this.
    
    Returns
    -------
    distances : np.array
        The distance each vehicle travels
    times : np.array
        The time each vehicle takes
    futile : np.array
        The number of futile deliveries for each vehicle
    delivered : list
        A list of all successful deliveries
    """
    s = copy(s)
    np.random.seed(seed)
    times = []
    distances = []
    futile = np.zeros(len(s.routes))
    delivered = []

    for i,route in enumerate(s.routes):
        times.append([])
        times[-1].append(0)
        distances.append([])
        distances[-1].append(0)
        for j in range(len(route)-1):
            distance, time, isfutile = update_function(route, j, times[-1][-1])
            distances[-1].append(distances[-1][-1] + distance)
            times[-1].append(times[-1][-1] + time)
            if isfutile:
                futile[i] += 1
            else:
                delivered.append(route[j])
                
    return distances, times, futile, delivered

def default_update_function(distance_matrix, time_matrix, time_windows):
    '''
    This time window policy makes the decision after arriving at the next place.
    The deliver man checks the time once arrived. 
    If the current time falls out of the time windows, then he will skip and go to the next place.
    '''
    f = default_distance_function(distance_matrix)
    g = default_time_function(time_matrix)
    def h(route, i, time):
        next_distance = f(route[i],route[i+1],time)
        next_time = g(route[i],route[i+1],time)
        if route[i+1] in time_windows:
            futile = time+next_time < time_windows[route[i+1]][0] or time+next_time > time_windows[route[i+1]][1]
        else:
            futile = True # why futile is true if it does not have a tw?
        return next_distance, next_time, futile

    return h

def update_function2(distance_matrix, time_matrix, time_windows):
    '''
    This time window policy makes the decision after arriving at the next place.
    The deliver man checks the time once arrived. 
    If the current time is earlier than the time windows, then he will wait till the availabe time.
    If the current time is later than the time windows, he will skip to next place.
    '''

    f = default_distance_function(distance_matrix)
    g = default_time_function(time_matrix)
    def h(route, i, time):
        next_distance = f(route[i],route[i+1],time)
        next_time = g(route[i],route[i+1],time)
        if route[i+1] in time_windows:
            if time+next_time < time_windows[route[i+1]][0]:
                # add on the waiting time
                next_time = time_windows[route[i+1]][0] - time
                futile = False
            elif time+next_time > time_windows[route[i+1]][0]: # second index of tw should be 1?
                # skip i+1 job
                futile = True
            else:
                futile = False
        else:
            futile = True
        return next_distance, next_time, futile

    return h

def default_update_function3(distance_matrix, time_matrix, time_windows):
    ''' Basically the same as above, but changed the format of time_windows to a np.array
    This time window policy makes the decision after arriving at the next place.
    The deliver man checks the time once arrived. 
    If the current time falls out of the time windows, then he will skip and go to the next place.
    '''
    f = default_distance_function(distance_matrix)
    g = default_time_function(time_matrix)

    def h(route, i, time):
        next_distance = f(route[i],route[i+1],time)
        next_time = g(route[i],route[i+1],time)
        futile = time+next_time < time_windows[route[i+1]][0] or time+next_time > time_windows[route[i+1]][1]
        return next_distance, next_time, futile

    return h

def update_function4(distance_matrix, time_matrix, time_windows):
    '''
    This time window policy makes the decision before arriving at the next place.
    The deliver man checks the time before departing from the current place. 
    If the estimated arriving time is earlier than the time windows, then he will wait till the availabe time.
    If the estimated arriving time is later than the time windows, he will skip the next place and reroute.
    '''

    f = default_distance_function(distance_matrix)
    g = default_time_function(time_matrix)
    def h(route, i, time):
        # route = [0, 3, 2, 1, 4, 0]
        next_distance = f(route[i],route[i+1],time)
        next_time = g(route[i],route[i+1],time)
        if time+next_time < time_windows[route[i+1]][0]:
            # add on the waiting time
            next_time = time_windows[route[i+1]][0] - time
            futile = False
        elif time+next_time > time_windows[route[i+1]][1]:
            # skip i+1 job and reroute
            futile = True
            # go straight to depot if the next place is depot after skipping
            if route[i+2] == 0:
                next_distance = f(route[i],route[i+2],time)
                next_time = g(route[i],route[i+2],time)
            else:
                # # get the rest of the places that need to visit
                # places_to_visit = route[i+2::]
                # if i != 0:
                #     places_to_visit.append(route[i])
                # places_to_visit.sort()
                # keys = list(np.arange(len(places_to_visit)))
                # # record both the places that their indices in rerouting
                # places_to_visit_dic = dict(zip(keys, places_to_visit))
                # # current place - starting place for rerouting
                # k = places_to_visit.index(route[i])
                # # slice the times for the places to visit
                # tm = time_matrix[places_to_visit]
                # tm = tm[:, places_to_visit]
                # # slice the time windows for the places to visit
                # w = time_windows[places_to_visit]
                # # print(tm)
                # route_new = rerouting(k, np.zeros((len(tm),len(tm))), tm, w)
                # route_n = [places_to_visit_dic[x] for x in route_new]
                # # print(route_n)

                route_new = rerouting1(i, route, distance_matrix,time_matrix, time_windows)
                print(route_new)

                next_distance = f(route_new[i],route_new[i+1],time)
                next_time = g(route_new[i],route_new[i+1],time)
        else:
            futile = False
        
        return next_distance, next_time, futile

    return h

def default_distance_function(distance_matrix):
    def f(i,j,time):
        return distance_matrix[i,j]
    return f

def default_time_function(time_matrix):
    def f(i,j,time):
        return time_matrix[i,j]
    return f

def default_futile_function(prob):
    def f(i,j,time):
        return np.random.rand() < prob
    return f

def tw_policy1(i, j, route, distances, times, windows):
    '''
    This time window policy makes the decision after arriving at the next place.
    The deliver man checks the time once arrived. 
    If the current time falls out of the time windows, then he will skip and go to the next place.
    '''
    # make the decision after arrival
    # out of time windows
    isfail = False
    print(times[i])
    if times[i] < windows[route[j+1]][0] or times[i] > windows[route[j+1]][1]:
        # skip j+1 job
        isfail = True
    return isfail

def tw_policy2(i, j, route, distances, times, windows, time_function):
    '''
    This time window policy makes the decision after arriving at the next place.
    The deliver man checks the time once arrived. 
    If the current time is earlier than the time windows, then he will wait till the availabe time.
    If the current time is later than the time windows, he will skip to next place.
    '''
    # make the decision after arrival
    # out of time windows
    if times[i] < windows[route[j+1]][0]:
        # add on the waiting time
        times[i] += windows[route[j+1]][0] - time_function(route[j], route[j+1], times[i])
    elif times[i] > windows[route[j+1]][0]:
        # skip j+1 job
        isfail = True
    return isfail

def collect_data(day:int, seed:int, solution:RoutingSolution, distances:list, times:list, futile:np.array, 
                delivered:np.array, arrival_days:list, time_windows:dict):
    data = {}
    key = 'day'+str(day)+'_'+str(seed)

    time_delivered = []
    for d in delivered:
        if d != 0:
            found = False
            for i,route in enumerate(solution.routes):
                for j,node in enumerate(route):
                    if node == d:
                        time_delivered.append(times[i][j])
                        found = True
                        break
                if found:
                    break
            if not found:
                time_delivered.append(-1) # Error. Hopefully negative time is obviously wrong.

    data[key] = {
        "number_of_packages": int(len(arrival_days)-1), # This could potentially be higher than the number of deliveries in the routes
        "number_of_vehicles": int(len(solution.routes)), # is it number of used vehicles or just a total number? ## Either way, I think we don't actually need this; we can get it from other info
        "distances": [int(sum(veh_dists)) for veh_dists in distances],
        "times": [int(sum(veh_times)) for veh_times in times],
        "deliveries_attempted": [int(len(route)-2) for route in solution.routes],#{[1,3,6,0,0]}, # successful deliveries or total deliveries? ## Attempted, so total. -2 for depo at start and end.
        "futile_deliveries": [int(f) for f in futile],
        "delivered_packages": {
            "days_taken": [int(day - arrival_days[i]) for i in delivered if i != 0], #[1,4,2,7,32,2],
            "time_delivered": [int(t) for t in time_delivered],
            "time_window": [[int(time_windows[i][0]),int(time_windows[i][1])] for i in delivered if i != 0] #[[2,4],[2,3],[2,3],[1,4],[1,2]] 
        },
        "undelivered_packages": {
            "days_taken": [int(day - arrival_days[i]) for i in range(len(arrival_days)) if i!=0 or i not in delivered],#[12,54,21,43,21],
            "time_window": [[int(time_windows[i][0]),int(time_windows[i][1])] for i in range(len(arrival_days)) if i!=0 or i not in delivered]#[[3,7],[2,7],[5,9],[1,3],[4,5]] 
        }
    }

    return data


def multiday(depots, sample_generator, dist_and_time, route_optimizer, simulator, n_days, day_start, day_end):
    """
    Paramters
    ---------
    depots : np.array
        2*n_depots array of longitudes and latitudes of the depots.
        This is set up to support multidepot problems. However, to do this properly we'll need to track which depots
        have which packages. Need to think about this more.
    sample_generator : function
        Takes no inputs, returns two lists, longitudes and latitudes of the packages.
    dist_and_time : function
        Takes longitudes and latitudes, and returns a distance matrix, a time matrix, and a array of time windows.
    route_optimizer : function
        Inputs are the depot numbers, the distance and time matrices, the time windows as a np.array,
        the current day, the day each package arrived, and the number of times each package was futile.
        Outputs are a set of vehicle routes, and a list of packages that were not scheduled.
    simulator : function
        Simulates the deliveries for a set of routes, given the routes, distances, times and time windows.
    n_days : int
        The number of days to simulate.
    day_start : int
        The time for the start of a day
    day_end : int
        The time for the end of a day
    """
    data = []
    delivery_lats = depots[0]
    delivery_lons = depots[1]
    n_depots = depots.shape[1]
    delivery_time_windows = np.array([[day_start, day_end] for i in range(n_depots)])
    arrival_days = np.zeros(n_depots)
    futile_count = np.zeros(n_depots)

    for day in range(n_days):
        # Generate data 
        lats, lons, new_time_windows = sample_generator(day)
        delivery_lats = np.append(delivery_lats,lats)
        delivery_lons = np.append(delivery_lons,lons)
        delivery_time_windows = np.vstack((delivery_time_windows,new_time_windows))
        arrival_days = np.append(arrival_days, [day for _ in range(len(lats))])
        futile_count = np.append(futile_count, np.zeros(len(lats)))

        # Get times and distances
        dm,tm = dist_and_time(delivery_lats, delivery_lons)
        if dm is None:
            # We've exceeded the map bounds. Stop here for now, but we should really handle this more gracefully.
            break
        dm = np.array(dm)
        tm = np.array(tm)
        
        # Calulate routes for the day TODO
        routes, unscheduled = route_optimizer(
            [i for i in range(n_depots)], 
            dm, tm, delivery_time_windows, 
            day, arrival_days, futile_count
        )
        if False:
            routes.plot(positions=[(delivery_lats[i], delivery_lons[i]) for i in range(len(delivery_lats))])
        futile_count[[i for i in range(len(delivery_lats)) if i not in unscheduled]] += 1

        # Simulate behaviour
        distances, times, futile, delivered = simulator(
            routes, dm, tm, delivery_time_windows, seed=day
        )

        # Data collection to save
        data.append(collect_data(day, 0, routes, distances, times, futile, delivered, arrival_days, delivery_time_windows))

        # Remove delivered packages
        undelivered = np.ones(len(delivery_lats), dtype=bool)
        undelivered[delivered] = False
        undelivered[[i for i in range(n_depots)]] = True
        delivery_lats = delivery_lats[undelivered]
        delivery_lons = delivery_lons[undelivered]
        delivery_time_windows = delivery_time_windows[undelivered]
        arrival_days = arrival_days[undelivered]
        futile_count = futile_count[undelivered]

    return data

def rerouting(current_start, distance_matrix, time_matrix, time_windows):
    '''
    This function finds the optimal routes from the current location to depot 'O'.

    Parameters
    ---------------
    current start: current starting place
    distance_matrix: original distance matrix
    time_matrix: original time matrix
    time_windows: original time windows

    Returns
    ---------------
    route: an optimal route from the current location to depot 'O'
    '''
    dm = default_distance_function(distance_matrix)
    tm = default_time_function(time_matrix)

    # compute rerouting time windows
    time_windows = np.vstack ((time_windows, np.array([0.,99999999999999.])) )
    print ("windows", str(time_windows)) 
    # compute rerouting time matrix
    time_matrix = rerouting_matrix(current_start, time_matrix)
    # printing result 
    print ("time_matrix", str(time_matrix)) 
    locs = time_matrix.shape[0] 
    depo = time_matrix.shape[0] - 1

    # solve the problem
    r = ORToolsRouting(locs, 1, depo)
    dim,ind = r.add_time_windows(time_matrix, time_windows, 1, 10, False, 'time')
    r.routing.SetArcCostEvaluatorOfAllVehicles(ind)
    s = r.solve()
    route = s.routes[0][1:-1]
    return route
    

def rerouting1(i, route, distance_matrix, time_matrix, time_windows):
    '''
    This function finds the optimal routes from the current location to depot 'O'.

    Parameters
    ---------------
    current start: current starting place
    distance_matrix: original distance matrix
    time_matrix: original time matrix
    time_windows: original time windows

    Returns
    ---------------
    route: an optimal route from the current location to depot 'O'
    '''
    # dm = default_distance_function(distance_matrix)
    # tm = default_time_function(time_matrix)

    # if route[i+2] == 0:
    #     next_distance = f(route[i],route[i+2],time)
    #     next_time = g(route[i],route[i+2],time)

    # get the rest of the places that need to visit
    places_to_visit = route[i+2::]
    if i != 0:
        places_to_visit.append(route[i])
    places_to_visit.sort()
    keys = list(np.arange(len(places_to_visit)))
    # record both the places that their indices in rerouting
    places_to_visit_dic = dict(zip(keys, places_to_visit))
    # current place - starting place for rerouting
    k = places_to_visit.index(route[i])

    # slice the distances for the places to visit
    dm = distance_matrix[places_to_visit]
    dm = dm[:, places_to_visit]
    # slice the times for the places to visit
    tm = time_matrix[places_to_visit]
    tm = tm[:, places_to_visit]
    # slice the time windows for the places to visit
    tw = time_windows[places_to_visit]

    # add tw for arbitrary depot
    tw = np.vstack ((tw, np.array([0.,99999999999999.])) )
    # compute rerouting time matrix
    tm = rerouting_matrix(k, tm)
    # compute rerouting distance matrix
    dm = rerouting_matrix(k, dm)
    # print ("time_matrix", str(tm)) # printing result 
    locs = tm.shape[0] 
    depo = tm.shape[0] - 1

    # solve the problem
    r = ORToolsRouting(locs, 1, depo)
    dim,ind = r.add_time_windows(tm, tw, 1, 10, False, 'time')
    r.routing.SetArcCostEvaluatorOfAllVehicles(ind)
    s = r.solve()
    route_new = s.routes[0][1:-1]

    # route_n = places_to_visit_dic[route_new]
    route_n = [places_to_visit_dic[x] for x in route_new]

    return route_n

def rerouting_matrix(k, matrix):
    '''
    This function computes the dm or tm needed for rerouting.

    Parameters
    ---------------
    k: current starting place
    matrix: original distance matrix or time matrix

    Returns
    ---------------
    matrix: dm or tm with an arbitrary depot 
    '''
    M = 99999999999999
    # add an arbitrary depot 'E'
    row_to_be_added = np.ones(matrix.shape[0]) * M
    # Adding row to numpy array 
    matrix = np.vstack ((matrix, row_to_be_added) ) 
    col_to_be_added = np.ones(matrix.shape[0]) * M
    # Adding col to numpy array 
    matrix = np.hstack ((matrix, np.atleast_2d(col_to_be_added).T) )
    # force an arc from 'E' to current place - to start from 'E'
    matrix[-1][k] = 0
    # force an arc from depot 'O' to 'E' - to arrive at 'O'
    matrix[0][-1] = 0

    return matrix
