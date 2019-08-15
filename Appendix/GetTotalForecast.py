# -*- coding: utf-8 -*-
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
FMIForecast = True
TMSForecast = True

TMSurl = "https://tie.digitraffic.fi/api/v2/data/road-conditions/45"
#roads = ["45"]
myroads = ["00045_009_00000_0_0"] #"00045_010_00000_0_0"
sep = "\t"
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
    import javax.xml.parsers.DocumentBuilderFactory

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

date_API_raw = TZdata['datetime']
date_API = date_API_raw[:-6]  # removing the UTC offset (+03:00) of date because python 2.7 datetime lib does not like it
APIDate = datetime.datetime.strptime(date_API, '%Y-%m-%dT%H:%M:%S.%f')
SystemDate = datetime.datetime.now() #getting system current time as datetime object

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
def ChangeDates(list, olddateformat, newdateformat,isutc):
    #changing date format.
    Newlist = []
    if isutc==True: #change UTC+0 to the current UTC of the location provided
        for eachdate in list:
            Newlist.append(((datetime.datetime.strptime(eachdate, olddateformat)) + datetime.timedelta(hours=utcoffset)).strftime(newdateformat)) #converts string from list in date object and convert back to desired date format str
        return Newlist
    else: #assumes date format from raw data is already in the current time
        for eachdate in list:
            Newlist.append(((datetime.datetime.strptime(eachdate, olddateformat)).strftime(newdateformat))) #converts string from list in date object and convert back to desired date format str
        return Newlist
#============================================================================================
#method to sum all the values in a list
#============================================================================================
def SumValuesInArray(forecastarrays):
    TotalPrecipitation = 0
    # if isinstance(forecastarrays[0], float):
    if isinstance(forecastarrays[0], list): #check for 2D lists
        for eachtimestep in range(len(forecastarrays)):
            for eachrangevalue in range(len(forecastarrays[0])): # forecastarrays[0] bc of 2D array. Check len only of 1D
                TotalPrecipitation += forecastarrays[eachtimestep][eachrangevalue]
    else:
        for eachtimestep in range(len(forecastarrays)):
            for eachrangevalue in range(len(forecastarrays)): # forecastarrays[0] bc of 2D array. Check len only of 1D
                TotalPrecipitation += forecastarrays[eachrangevalue]
    # else:
    #     for eachvalue in range(len(forecastarrays)): # transform the items in the list to float before performing the some. i.e. In case they are strings
    #         forecastarrays[eachvalue] = float(forecastarrays[eachvalue])
    #     for eachtimestep in range(len(forecastarrays)):
    #         for eachrangevalue in range(len(forecastarrays[0])): # forecastarrays[0] for the second dimension of the array
    #             TotalPrecipitation += forecastarrays[eachtimestep][eachrangevalue]

    return TotalPrecipitation
#============================================================================================
# Inputs used for the next methods.
#============================================================================================
timeNow = datetime.datetime.strftime(datetime.datetime.now(), "%d.%m.%Y %H:%M:%S")
date = [s.replace('Z','') for s in date] #take away the Z in the end of the date format bc python 2. does not work well with this format in datetime lib
Newdate = ChangeDates(date, '%Y-%m-%dT%H:%M:%S', "%d.%m.%Y %H:%M:%S", True)#call changedates method
#NumberOfFiles = 3 #3 files for Rain and 3 files for Snow according to the range configuration of "intensities"

#============================================================================================
# Method used to write timeSeries in external files and also update them in fluidit's model
#============================================================================================
def writefiles(provider, forecastparameter, datearray, valuearray, updatemodel, nfiles):
    for eachfile in range(nfiles): #writes to an external file
        file1 = open(os.path.join(ModelDirectory, "TS%d_%s.%sForecast.txt" % (eachfile, provider, forecastparameter)), "w")
        for L in range(len(valuearray)):
            if provider == 'TMS' and (forecastparameter == 'Rain' or forecastparameter == 'Snow'): #Condition because of the range as described in "intensities"
                file1.writelines(str(datearray[L]) + sep + str(valuearray[L][eachfile]) + '\n') #array 2D for valuearray
            else:
                file1.writelines(str(datearray[L]) + sep + str(valuearray[L]) + '\n')
        file1.close()

    if updatemodel == True: # writes directly to the model
        for eachfile in range(nfiles):
            TSname = "TS%d_%s.%sForecast" % (eachfile, provider, forecastparameter)
            NewTS = scenario.findComponent(TSname, TimeSeries)  # i.e. find TimeSeries by its name in TimeSeries model "xml" file
            print(NewTS)
            NewValues = []
            for eachtime in range(len(valuearray)):
                if provider == 'TMS' and (forecastparameter == 'Rain' or forecastparameter == 'Snow'):  # Condition because of the range as described in "intensities"
                    NewValues.append(TimeSeries.Entry(NewTS, str(datearray[eachtime]), float(valuearray[eachtime][eachfile]))) #calls inner class in TimeSeries that asks the TimeSeries Name, date, and value)
                else:
                    NewValues.append(TimeSeries.Entry(NewTS, str(datearray[eachtime]), float(valuearray[eachtime])))
            NewTS.setValues(NewValues)

    #Open the file back and read the contents to print in the console
    for eachfile in range(nfiles):
        file2=open(os.path.join(ModelDirectory, "TS%d_%s.%sForecast.txt" % (eachfile, provider ,forecastparameter)), "r")
        if file2.mode == 'r':
            contents =file2.read()
            print(contents)
            print("==============" + "\n")
        file2.close()

#============================================================================================
# Display warning if the dates and hours from Date-time API, OS, and forecast do not match
#============================================================================================
def checkforecast(datelistfirstvalue, datestringformat, provider):
    ForecastDate = datetime.datetime.strptime(datelistfirstvalue, datestringformat)#first date returned of the forecast

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
            print('Warning: %s Forecast dates different then API dates!' % provider)
        if yearlist[c][2] != yearlist[c][1]:  # if the forecast is different
            print('Warning: %s Forecast dates different then Op. System dates!' % provider)

    if yearlist[3][2] < yearlist[3][0]:
        print('Warning: %s Forecast hours behind APIs time schedule'% provider)
    if yearlist[3][2] < yearlist[3][1]:
        print('Warning: %s Forecast hours behind Op. System time schedule'% provider)
    if yearlist[3][2] < yearlist[3][0] and yearlist[3][2] < yearlist[3][1]:
        print('Warning: %s Forecast time behind current time: No actual forecast data provided'% provider)


#============================================================================================
#============================================================================================
#============================================================================================
# Start of FMI data collection
#============================================================================================
#============================================================================================
#============================================================================================
# Purpose: Retrieve forecast data from Finnish Metereological Institute (FMI) and Traffic Management Suomi (TMS)
# Inputs: Location by latitude and Longitude coordinates and parameter of interest (i.e. precipitation, temperature, windspeed, etc)
# Outputs: FMI supports all available parameters and it will be returned as a time series. TMS currently supports only Precipitation

#============================================================================================
# User Inputs - FMI
#============================================================================================
inputfilename = 'FMI_XML_Forecast.xml'
outputfilename = 'FMI_Forecast.txt'
timestep = 60 #in minutes
locatelatlon = True
locateplace = False
sep = '\t' #include separator desired for output file i.e '\t' for tab delimited ',' for csv
FMIurl = "http://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=getFeature&storedquery_id=fmi::forecast::"
lat = 60.55922 # hyvinkää station FMISID 101130: 60.59589, Center of Jokela Town: 60.55922, GeoName Jokela Lat: 60.55000
lon = 24.97789 # hyvinkää station FMISID 101130: 24.80297, Center of Jokela Town: 24.97789, GeoName Jokela Lon: 24.98330
FMIForecastModel = 'harmonie' #hirlam or harmonie
place = 'Jokela'
parameters = 'PrecipitationAmount' #Temperature, PrecipitationAmount
elementtime = '{http://www.opengis.net/waterml/2.0}time' # element in XML storing TIME attributes
elementvalue = '{http://www.opengis.net/waterml/2.0}value' # element in XML storing VALUE attributes
ModelDirectory = "C:/Users/PedroAlmeida/Fluidit Oy/Grundfos - WWNC/C Work" #location where the Forecast files will be written to be then used as timeSeries in the model

#============================================================================================
# Access FMI open data in XML format, Copy data and write to a file
#============================================================================================
if locateplace + locatelatlon == 2:
    print('ERROR: Choose only one option of location - Latlon or City Name')
    exit()
if locatelatlon == True and locateplace == False:
    url = FMIurl + FMIForecastModel + '::surface::point::timevaluepair' + '&latlon=' + str(lat) + ',' + str(lon) + '&parameters=' + parameters + '&timestep=' + str(timestep)
elif locateplace == True and locatelatlon == False:
    url = FMIurl + FMIForecastModel + '::surface::point::timevaluepair' + '&place=' + place + '&parameters=' + parameters + '&timestep=' + str(timestep)
r = urlopen(url).read()
#open(inputfilename, 'wb').write(r)
#tree = et.parse(inputfilename)
#tree = et.parse(r)
root = et.fromstring(r)
#root = tree.getroot()
print(url)

#============================================================================================
# Read Time and Value from XML file and return two arrays
#============================================================================================
cone = [] # array for column one containing Time
ctwo = [] # array for column one containing Value
for elementtime in root.iter(elementtime):
    cone.append(elementtime.text)
for elementvalue in root.iter(elementvalue):
    ctwo.append(elementvalue.text)

#============================================================================================
# Check if dates and time recordings' total number match with the parameter of the forecast
#============================================================================================
ForecastRange = 0
if len(cone)!= len(ctwo):
    print('Warning: Time and Values do not have the same range! Review input data')
else:
    ForecastRange = len(cone)
    print(ForecastRange, ' values returned with ',timestep, ' minutes timestep. Total time forecasted of ', (ForecastRange*timestep)/60, 'hours')

#============================================================================================
# Treatment of FMI data: change dates format, ctwo list with strings to FMIRainvalues list with floats, etc.
#============================================================================================

cone = [s.replace('Z','') for s in cone] #take away the Z in the end of the date format bc python 2. does not work well with this format in datetime lib
FMIdate = ChangeDates(cone, '%Y-%m-%dT%H:%M:%S', "%m/%d/%Y %H:%M", True)#call changedates method

#check if first date of FMI forecast is behind the current time and remove it from FMIdate list if so
FMIdatetime = []
for eachdate in range(len(FMIdate)): #store FMI forecast dates as a datetime object
    FMIdatetime.append(datetime.datetime.strptime(FMIdate[eachdate], "%m/%d/%Y %H:%M"))
if FMIdatetime[0].hour < APIDate.hour:
    FMIdate.pop(0) #pop the element in index 0 of FMI date list and value
    ctwo.pop(0)
    print('Warning: FMI Forecast provides the first time (hour) before the Op. System time (hour). The first value was left out of simulation(s)')
if FMIdatetime[0].hour < SystemDate.hour:
    print('Warning: FMI Forecast provides the first time (hour) before the Op. System time (hour)')

FMIRainvalues = []
for eachvalue in range(len(ctwo)):  # transform the items in the list to float before going for the next step performing the sum. i.e. In case they are strings
    FMIRainvalues.append(float(ctwo[eachvalue]))

#============================================================================================
# print output to a file and update the model TS
#============================================================================================

fileFMI = open(os.path.join(ModelDirectory, "TS_FMI.%sForecast.txt" % FMIForecastModel), "w")
L = 0
for L in range(len(FMIdate)):
    fileFMI.writelines(str(FMIdate[L]) + sep + str(FMIRainvalues[L]) + '\n')
fileFMI.close()
#Open the file back and read the contents to print in the console
fileFMIr = open(os.path.join(ModelDirectory, "TS_FMI.%sForecast.txt" % FMIForecastModel), "r")
if fileFMIr.mode == 'r':
    contents =fileFMIr.read()
    print("================================" + "\n"
            + "FMI Forecast Model: " + FMIForecastModel + "\n" 
          "================================" + "\n"
          + contents)
fileFMIr.close()
#




#============================================================================================
#============================================================================================
# End of FMI data collection
#============================================================================================
#============================================================================================


#============================================================================================
#============================================================================================
# Start of shared actions FMI and TMS
#============================================================================================
#============================================================================================



# print(ctwo)
# if isinstance(ctwo[0], float):
#     a = 'it is float'
# else:
#     a = 'it is not'
#
# print(a)
#
# for eachvalue in range(len(ctwo)):  # transform the items in the list to float before performing the some. i.e. In case they are strings
#     ctwo[eachvalue] = float(ctwo[eachvalue])
# print(ctwo)

#============================================================================================
#Return the type of precipitation forecasted. If True, simulation can be runned.
#============================================================================================

if SumValuesInArray(RainForecastValues) and SumValuesInArray(SnowForecastValues) > 0:
    TMS_RainOccurrence = True
    TMS_SnowOccurrence = True
if SumValuesInArray(RainForecastValues) and SumValuesInArray(SnowForecastValues) == 0:
    TMS_RainOccurrence = False
    TMS_SnowOccurrence = False
if SumValuesInArray(RainForecastValues) == 0 and SumValuesInArray(SnowForecastValues) > 0:
    TMS_RainOccurrence = False
    TMS_SnowOccurrence = True
if SumValuesInArray(RainForecastValues) > 0 and SumValuesInArray(SnowForecastValues) == 0:
    TMS_RainOccurrence = True
    TMS_SnowOccurrence = False
if SumValuesInArray(FMIRainvalues) > 0:
    FMI_RainOccurrence = True
else:
    FMI_RainOccurrence = False
#============================================================================================
# Write and Update timeSeries only if there is a forecasted precipitation
#============================================================================================
tmsnumberoffiles = 1
fminumberoffiles = 1

if TMSForecast == True:
    if TMS_RainOccurrence == True:
        rainfiles = 3
        writefiles('TMS', "Rain", Newdate, RainForecastValues, UpdateModelTS, rainfiles)

    if TMS_SnowOccurrence == True:
        snowfiles = 3
        writefiles('TMS', "Snow", Newdate, SnowForecastValues, UpdateModelTS, snowfiles)

    # checkforecast(Newdate[0], "%m.%d.%Y %H:%M", 'TMS')

    writefiles('TMS', "Temp", Newdate, temp, UpdateModelTS, tmsnumberoffiles)

if FMIForecast == True:
    if FMI_RainOccurrence == True:
        writefiles('FMI', "Rain", FMIdate, FMIRainvalues, UpdateModelTS, fminumberoffiles)

    # checkforecast(FMIdate[0], "%m.%d.%Y %H:%M", 'FMI')

#============================================================================================
# Print Forecast MetaData
#============================================================================================
if TMSForecast == True:
    TMSForecastMeta = open(os.path.join(ModelDirectory,"TMS Forecast Metadata.txt"), "w")

    TMSForecastMeta.write("=========================================="+ "\n"
                       + "Data from Traffic Management Finland (TMS)" + "\n"
                       + "=========================================="+ "\n" + "\n"
                       + "Last retrieve from API on:    %s" %timeNow  + "\n"
                       + "Road(s) selected:             %s" %str(myroads) + "\n"
                       + "Number of files created:      %d" %tmsnumberoffiles + "\n"
                       + "TMS API URL:                  %s" %TMSurl + "\n"
                       + "More metadata available on:    https://tie.digitraffic.fi/api/v1/metadata/forecast-sections" + "\n"
                       + "==========================================" + "\n" + "\n"
                       + "Description of weather conditions available in the forecast :  %s" %str(WeatherConditions) + "\n"
                       + "Snow :  %s" %str(SnowForecastValues) + "\n"
                       + "Rain :  %s"%str(RainForecastValues))
    TMSForecastMeta.close()

if TMSForecast == True:
    FMIForecastMeta = open(os.path.join(ModelDirectory, "FMI Forecast Metadata.txt"), "w")
    #
    # FMIForecastMeta.write("==========================================" + "\n"
    #                       + "Data from Finnish Metereological Institute (FMI)" + "\n"
    #                       + "==========================================" + "\n" + "\n"
    #                       + "Last retrieve from API on:    %s" % timeNow + "\n"
    #                       + "Road(s) selected:             %s" % str(myroads) + "\n"
    #                       + "Number of files created:      %d" % tmsnumberoffiles + "\n"
    #                       + "TMS API URL:                  %s" % TMSurl + "\n"
    #                       + "More metadata available on:    https://tie.digitraffic.fi/api/v1/metadata/forecast-sections" + "\n"
    #                       + "==========================================" + "\n" + "\n"
    #                       + "Description of weather conditions available in the forecast :  %s" % str(WeatherConditions) + "\n"
    #                       + "Snow :  %s" % str(SnowForecastValues) + "\n"
    #                       + "Rain :  %s" % str(RainForecastValues))


    FMIForecastMeta.close()