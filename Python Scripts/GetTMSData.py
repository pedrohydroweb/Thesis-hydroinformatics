import xml.etree.ElementTree as et

import json
import datetime
import os.path


try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request, HTTPError

#Roads metadata "https://tie.digitraffic.fi/api/v1/metadata/forecast-sections"
# Get json file from TMS API
#==================================================================
FMIForecast = False
TMSForecast = True

TMSurl = "https://tie.digitraffic.fi/api/v2/data/road-conditions/45"
#roads = ["45"]
myroads = ["00045_009_00000_0_0"] #"00045_010_00000_0_0"
sep = ","
ModelDirectory = "C:/Users/PedroAlmeida/Fluidit Oy/Grundfos - WWNC/C Work" #location where the Forecast files will be written to be then used as timeSeries in the model C:/Users/PedroAlmeida/Fluidit Oy/Grundfos - WWNC/C Work
UpdateModelTS = False# #option to make available the update in the models if the code is imported through jython
TimeZoneAPI = "http://worldtimeapi.org/api/timezone/"
TimeZone = "Europe/Helsinki"
#==================================================================

if UpdateModelTS == True:
    from fi.fluidit.simulator import ConnectionFinder, TimeSeries
    from fi.fluidit.ui import Util
    from fi.fluidit.result import *
    from fi.fluidit.model import *
    from fi.fluidit.sewer.model.results import *
    from fi.fluidit.sewer.model import *
    model = Util.getActiveModel()
    scenario = model.active

intensities = {

    "NO_RAIN_DRY_WEATHER": [0,0,0], #<2 mm/h #1= Rain intensity
    "LIGHT_RAIN": [0.2,2.25,2.5], #2= Rain intensity mm/h
    "RAIN": [2.5,5,7.5], #3= Rain intensity mm/h
    "HEAVY_RAIN": [7.6,9.5,11.5], #4= Rain intensity mm/h - TMS just inform that it is greater than 7.6 mm/h. The other values are 25% and 50% higher
    "LIGHT_SNOWFALL": [0.2,0.55,0.9], #5= snowing intensity cm/h
    "SNOWFALL": [1, 2, 3], #6= snowing intensity cm/h
    "HEAVY_SNOWFALL": [3,3.75,4.5] #7= snowing intensity cm/h - TMS just inform that it is greater than 3cm/h. The other values are 25% and 50% higher
}


#with urlopen(TMSurl) as response:
response = urlopen(TMSurl).read()
TMSdata = json.loads(response) #get TMSdata and write as a python dic
#============================================================================================
# Get UTC offset integer from provided API. Returns 'utcoffset' i.e. in case of Finland it
# can be either 2 or 3F hours
#============================================================================================
UrlTimeAPI = TimeZoneAPI + TimeZone
TimeAPIsource = urlopen(UrlTimeAPI).read()
TZdata = json.loads(TimeAPIsource)
TZlist = []
for c in TZdata['utc_offset']:
    TZlist.append(c)
utcoffset = int(TZlist[2])

#============================================================================================
# Parse through Json data from TMS API and save as lists the dates and values
#============================================================================================
mydata = filter(lambda x: x['id'] in myroads, TMSdata['weatherData'])
date, temp, weatherSymbol, fname, RainForecastValues, type, WeatherConditions, SnowForecastValues = [],[],[],[],[],[],[],[] #variables used to store forecast values
for road in mydata:
    for i in road["roadConditions"]:
        if i["type"] == "FORECAST":
            type.append(i["type"])
            date.append(i["time"])
            temp.append(i["temperature"])
            weatherSymbol.append(i["weatherSymbol"]) #https://corporate.foreca.com/en/resources/foreca-symbols image of each symbol
            fname.append(i["forecastName"]) #forecastName
            WeatherConditions.append([i["forecastConditionReason"]["precipitationCondition"]])
            if i["forecastConditionReason"]["precipitationCondition"] is not "LIGHT_SNOWFALL" or "SNOWFALL" or "HEAVY_SNOWFALL":
                RainForecastValues.append(intensities[i["forecastConditionReason"]["precipitationCondition"]])
                SnowForecastValues.append([0,0,0])
            else:
                SnowForecastValues.append(intensities[i["forecastConditionReason"]["precipitationCondition"]])
                RainForecastValues.append([0,0,0])

#============================================================================================
#function to change date format inside a list and update time zone. Inputs: List and desired
# date format i.e. "%d.%m.%Y %H:%M:%S"
#============================================================================================
def ChangeDates(list, olddateformat, newdateformat):
    Newlist = []
    for eachdate in list:
        Newlist.append(((datetime.datetime.strptime(eachdate, olddateformat)) + datetime.timedelta(hours=utcoffset)).strftime(newdateformat)) #converts string from list in date object and convert back to desired date format str
    return Newlist

#============================================================================================
#method to sum all the values in a list
#============================================================================================
def SumValuesInArray(forecastarrays):
    TotalPrecipitation = 0
    for eachtimestep in range(len(forecastarrays)):
        for eachrangevalue in range(len(forecastarrays[0])): # forecastarrays[0] for the second dimension of the array
            TotalPrecipitation += forecastarrays[eachtimestep][eachrangevalue]
    return TotalPrecipitation

#============================================================================================
#Return the type of precipitation forecasted. If True, simulation can be runned.
#============================================================================================
RainOccurrence = 1
SnowOccurrence = 1
if SumValuesInArray(RainForecastValues) and SumValuesInArray(SnowForecastValues) > 0:
    RainOccurrence = True
    SnowOccurrence = True
if SumValuesInArray(RainForecastValues) and SumValuesInArray(SnowForecastValues) == 0:
    RainOccurrence = False
    SnowOccurrence = False
if SumValuesInArray(RainForecastValues) == 0 and SumValuesInArray(SnowForecastValues) > 0:
    RainOccurrence = False
    SnowOccurrence = True
if SumValuesInArray(RainForecastValues) > 0 and SumValuesInArray(SnowForecastValues) == 0:
    RainOccurrence = True
    SnowOccurrence = False

#============================================================================================
# Inputs used for the next methods.
#============================================================================================
timeNow = datetime.datetime.strftime(datetime.datetime.now(), "%d.%m.%Y %H:%M:%S")
date = [s.replace('Z','') for s in date] #take away the Z in the end of the date format bc python 2. does not work well with this format in datetime lib
Newdate = ChangeDates(date, '%Y-%m-%dT%H:%M:%S', "%d.%m.%Y %H:%M:%S")#call changedates method
NumberOfFiles = 3 #3 files for Rain and 3 files for Snow according to the range configuration of "intensities"

#============================================================================================
# Method used to write timeSeries in external files and also update them in fluidit's model
#============================================================================================
def writefiles(provider, forecastparameter, datearray, valuearray, updatemodel):
    for eachfile in range(NumberOfFiles):
        file1 = open(os.path.join(ModelDirectory, "TS%d_%s.%sForecast.txt" % (eachfile, provider, forecastparameter)), "w")
        for L in range(len(valuearray)):
            file1.writelines(str(datearray[L]) + sep + str(valuearray[L][eachfile]) + '\n')
        file1.close()

    if updatemodel == True:
        for eachfile in range(NumberOfFiles):
            TSname = "TS%d_%s.%sForecast" % (eachfile, provider, forecastparameter)
            NewTS = scenario.findComponent(TSname, TimeSeries)  # i.e. find TimeSeries by its name in TimeSeries model "xml" file
            print(NewTS)
            NewValues = []
            for eachtime in range(len(valuearray)):
                NewValues.append(TimeSeries.Entry(NewTS, str(datearray[eachtime]), float(valuearray[eachtime][eachfile]))) #calls inner class in TimeSeries that asks the TimeSeries Name, date, and value)
            NewTS.setValues(NewValues)

    #Open the file back and read the contents to print in the console
    for eachfile in range(NumberOfFiles):
        file2=open(os.path.join(ModelDirectory, "TS%d_%s.%sForecast.txt" % (eachfile, provider ,forecastparameter)), "r")
        if file2.mode == 'r':
            contents =file2.read()
            print(contents)
            print("==============" + "\n")
        file2.close()

#============================================================================================
# Display warning if the dates and hours from Date-time API, OS, and forecast do not match
#============================================================================================
date_API_raw = TZdata['datetime']
date_API = date_API_raw[:-6] #removing the UTC offset (+03:00) of date because python 2.7 datetime lib does not like it
APIDate = datetime.datetime.strptime(date_API, '%Y-%m-%dT%H:%M:%S.%f')
SystemDate = datetime.datetime.now()
ForecastDate = datetime.datetime.strptime(Newdate[0], "%d.%m.%Y %H:%M:%S")#first date returned of the forecast

dateMap = {
        'year':     [APIDate.year, SystemDate.year, ForecastDate.year],
        'month':    [APIDate.month, SystemDate.month, ForecastDate.month],
        'day':      [APIDate.day, SystemDate.day, ForecastDate.day],
        'hour':     [APIDate.hour, SystemDate.hour, ForecastDate.hour]
}

yearlist = []
for i in dateMap:
    yearlist.append(dateMap[i])

for c in range(len(yearlist[2])):
    if yearlist[c][2] != yearlist[c][0]: #if the forecast is different
        print('Warning: Forecast dates different then API dates!')
    if yearlist[c][2] != yearlist[c][1]:  # if the forecast is different
        print('Warning: Forecast dates different then Op. System dates!')

if yearlist[3][2] < yearlist[3][0]:
    print('Warning: Forecast hours behind APIs time schedule')
if yearlist[3][2] < yearlist[3][1]:
    print('Warning: Forecast hours behind Op. System time schedule')
if yearlist[3][2] < yearlist[3][0] and yearlist[3][2] < yearlist[3][1]:
    print('Warning: Forecast time behind current time: No actual forecast data provided')

#============================================================================================
# Write and Update timeSeries only if there is a forecasted precipitation
#============================================================================================
if TMSForecast == True:
    if RainOccurrence == True:
        writefiles('TMS', "Rain", Newdate, RainForecastValues, UpdateModelTS)
    if SnowOccurrence == True:
        writefiles('TMS', "Snow", Newdate, SnowForecastValues, UpdateModelTS)

if FMIForecast == True:
    if RainOccurrence == True:
        writefiles('FMI', "Rain", Newdate, RainForecastValues, UpdateModelTS)
    if SnowOccurrence == True:
        writefiles('FMI', "Snow", Newdate, SnowForecastValues, UpdateModelTS)


#============================================================================================
# Print Forecast MetaData
#============================================================================================
ForecastMeta = open(os.path.join(ModelDirectory,"TMS Forecast Metadata.txt"), "w")

ForecastMeta.write("=========================================="+ "\n"
                   + "Data from Traffic Management Finland (TMS)" + "\n"
                   + "=========================================="+ "\n" + "\n"
                   + "Last retrieve from API on:    %s" %timeNow  + "\n"
                   + "Road(s) selected:             %s" %str(myroads) + "\n"
                   + "Number of files created:      %d" %NumberOfFiles + "\n"
                   + "TMS API URL:                  %s" %TMSurl + "\n"
                   + "More metadata available on:    https://tie.digitraffic.fi/api/v1/metadata/forecast-sections" + "\n"
                   + "==========================================" + "\n" + "\n"
                   + "Description of weather conditions available in the forecast :  %s" %str(WeatherConditions) + "\n"
                   + "Snow :  %s" %str(SnowForecastValues) + "\n"
                   + "Rain :  %s"%str(RainForecastValues))
ForecastMeta.close()


#============================================================================================
#============================================================================================
#============================================================================================
# Retrieve data From FMI
#============================================================================================
#============================================================================================
#============================================================================================
