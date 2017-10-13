from time import sleep
import gps3

def read():
    return -1, -1, -1

    the_connection = gps3.GPSDSocket()
    the_fix = gps3.Fix()

    try:
        for new_data in the_connection:
            if new_data:
                the_fix.refresh(new_data)
            if not isinstance(the_fix.TPV['lat'], str):  # check for valid data
                speed = the_fix.TPV['speed']
                latitude = the_fix.TPV['lat']
                longitude = the_fix.TPV['lon']
                altitude = the_fix.TPV['alt']
                #sleep(2)
	        the_connection.close()
    except:
    	return latitude, longitude, altitude
    return latitude, longitude, altitude
