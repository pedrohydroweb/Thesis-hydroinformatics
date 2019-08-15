##
import plotly
import plotly.plotly as py
import plotly.graph_objs as go
import os
import numpy as np
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy import signal
import datetime


nondata_value = -999
nondata_value_as = np.nan #value to replace nondata_value
upload_to_plotly = True
replace_zeros = True
scatter_plot_axis_label = 'Inflow [l/s]'
directory = 'C:/Users/PedroAlmeida/Fluidit Oy/Grundfos - WWNC/C Work/Pre-processing/TimeSeries Analysis/Flow data'
datatime_step = 'H'
tseries_name = 'Jokela_inflow_2018_ps.csv'
sep = ' '
date_rng = pd.date_range(start='1/1/2018', end='12/31/2018', freq='H')


# my_data = genfromtxt('my_file.csv', delimiter=',')




#=====================================================================================================================
#Functions to be used
#=====================================================================================================================
def ChangeDates(list, olddateformat, newdateformat, isutc=False, customoffset=0):
    #changing date format.
    Newlist = []
    if isutc==True: #change UTC+0 to the current UTC of the location provided
        for eachdate in list:
            Newlist.append(((datetime.datetime.strptime(eachdate, olddateformat))
                            + datetime.timedelta(hours=utcoffset)).strftime(newdateformat)) #converts string from list in date object and convert back to desired date format str
        return Newlist
    elif customoffset != 0 and isutc == False:
        for eachdate in list:
            Newlist.append(((datetime.datetime.strptime(eachdate, olddateformat))
                            + datetime.timedelta(hours=customoffset)).strftime(newdateformat))  # converts string from list in date object and convert back to desired date format str
        return Newlist
    elif customoffset != 0 and isutc == True:
        return print('Please choose UTC or Customized Offset, not both. Set "isutc" to False or "customoffset" to 0')
    else: #assumes date format from raw data is already in the current time
        for eachdate in list:
            Newlist.append(((datetime.datetime.strptime(eachdate, olddateformat)).strftime(newdateformat))) #converts string from list in date object and convert back to desired date format str
        return Newlist


def writefiles(provider, parameter, datearray, valuearray):
     file1 = open(os.path.join(directory, "TS_%s.%s.dat" % (provider, parameter)), "w")
     for L in range(len(valuearray)):
        file1.writelines(str(datearray[L]) + sep + str(valuearray[L]) + '\n')
     file1.close()
#=====================================================================================================================

tseries_path = open(os.path.join(directory, tseries_name), "r")

tseries_pd_raw = pd.read_csv(tseries_path,  header=0, parse_dates=[0], index_col=0, squeeze=True)# read the csv file and store the info as pandas series

#=======================================================================
# Find missing dates in time series, fill missing dates with specified
# values and print an external file with the missing dates
#=======================================================================
#tseries_pd_raw_complete = tseries_pd_raw.resample(datatime_step).asfreq().fillna(nondata_value) #fill the missing dates and replace the value by the missing data number given by the user
tseries_pd_raw_complete = tseries_pd_raw.reindex(date_rng,fill_value=nondata_value) #fill the missing dates and replace the value by the missing data number given by the user


missing_steps_a = tseries_pd_raw_complete[tseries_pd_raw_complete == nondata_value].index # find missing dates by the nondata_value and store as pandas.timestamp

missing_steps = missing_steps_a.astype(str) #convert timestamp to string before printing to an external file

# Loop to print missing dates to an external file
with open(os.path.join(directory, 'Missing_Steps.txt'), 'w') as f:
    for item in missing_steps:
        f.write("%s\n" % item)

tseries_pd_raw_complete_filled = tseries_pd_raw_complete.replace(to_replace = nondata_value, value = nondata_value_as) #replace the missing data values for user specified value

tseries_pd_raw_complete_filled_filtered = tseries_pd_raw_complete_filled.mask(tseries_pd_raw_complete_filled > 150) # filter-out outliers

if replace_zeros == True:
    tseries_pd_raw_complete_filled_filtered_nan = tseries_pd_raw_complete_filled_filtered.replace(to_replace = 0, value = nondata_value_as) #replace zeroes for user specified value
    #tseries = tseries_pd_raw_complete_filled_filtered_nan.fillna(method='ffill') # fill Nan values with the previous
    tseries = tseries_pd_raw_complete_filled_filtered_nan.interpolate()  # fill Nan values with the previous .i.e. some other arguments could be passed such as (method='polynomial', order=3)
# a = tseries.to_frame()
# c = a.replace(to_replace = nondata_value_as, value = np.nan)
# c.plot()
# print(c)


#=============================================================================================
# Print as SWMM time Series data .dat
#=============================================================================================
# data has to be %m/%d/%y and tab delimited such as:
# 06/16/2019 23:00	0.0 ,   06/17/2019 00:00	0.0


# rename tseries dates and values
tseries_values_input = tseries_pd_raw_complete_filled.values #get only the values of raw tseries and store in a numpy-ndarray
tseries_values_output = tseries.values #get only the values of treated tseries and store in a numpy-ndarray

tseries_values_input_list = tseries_pd_raw_complete_filled.values.tolist()
tseries_values_output_list = tseries.values.tolist()


tseries_dates = pd.to_datetime(tseries_pd_raw_complete.index)  # get only the dates and store to an object = panda datetimes.datetimeindex
tseries_dates_input = tseries_dates.astype(str).tolist() #convert raw dates input to python list of string elements


tseries_dates_output = ChangeDates(tseries_dates_input, '%Y-%m-%d %H:%M:%S', "%m/%d/%Y %H:%M", False, 1) #new dates list


tseries_values_output_smoothed = signal.savgol_filter(tseries_values_output, 11, 5)

writefiles('Tuusula', 'Inflow', tseries_dates_output, tseries_values_output_smoothed)


# tseries.plot()
# b = tseries.to_csv(index=True, header=False)
# #
# print(b)
#
# f2 = open(os.path.join(directory, 'Missing_Steps_.txt'), 'w')
# f2.write(b)
# f2.close()

#=========================================================================================================



print('====================================================', '\n',
      'First date of input tseries: ', tseries_dates_input[0], '\n',
      'Last date of input tseries: ', tseries_dates_input[-1], '\n',
      '====================================================', '\n')

print('====================================================', '\n',
      'First date of output tseries: ', tseries_dates_output[0], '\n',
      'Last date of output tseries: ', tseries_dates_output[-1], '\n',
      '====================================================', '\n')




#=========================================================================================================
# Information about tseries loaded
#=========================================================================================================
monthlymean = tseries.resample('M').mean()
ranges = [-1,0,2,5,10,20,30,40,50,60,70,80,90,100,150,1000]
hist_input = tseries.groupby(pd.cut(tseries.values, ranges)).count()
hist_output = tseries.groupby(pd.cut(tseries.values, ranges)).count()
# print(type(hist))
# print(hist)
# hist.hist()
# plt.show()

tseries_mean = tseries.mean() #find time series mean
print(tseries_mean)


t_asc_ = tseries.sort_values()



tseries_values_asc_input = np.sort(tseries_values_input, axis=None) #organize values in ascending order and an array
tseries_values_dsc_input = tseries_values_asc_input[::-1] #organize values in descending order and an array
print(tseries_values_asc_input)
print(tseries_values_dsc_input)

tseries_values_asc_output = np.sort(tseries_values_output, axis=None) #organize values in ascending order and an array
tseries_values_dsc_output = tseries_values_asc_output[::-1] #organize values in descending order and an array
print(tseries_values_asc_output)
print(tseries_values_dsc_output)


# Create data
N = 500
x = [tseries_values_asc_input, tseries_values_asc_output]
y = [tseries_values_asc_input, tseries_values_asc_output]
plot_tittle = ['Raw Inflow Data', 'Processed Inflow Data']
colors = (0,0,0)
area = np.pi*3

# Plot
for eachts in range(2):
    plt.scatter(x[eachts], y[eachts], s=area, c=colors, alpha=0.5)
    plt.title(plot_tittle[eachts])
    plt.xlabel(scatter_plot_axis_label)
    plt.ylabel(scatter_plot_axis_label)
    plt.show()

#=========================================================================================================



if upload_to_plotly == True:
    plotly.tools.set_credentials_file(username='peco20', api_key='5Xdi4hkQrSgajpNkugk4')
    # x = dates
    #x = date_rng
    x = tseries_dates_input
    y_raw_filled = tseries_pd_raw_complete_filled_filtered_nan.values
    y_raw = tseries_pd_raw.values
    y = tseries_values_output_smoothed
    y_noise = tseries_values_output

    trace4 = go.Scatter(
        x=x,
        y=y,
        mode='lines',
        line=dict(
            # size=2,
            color='rgb(0, 0, 0)',
            shape='linear'
        ),
        # name='Sine'
        name='treated: Inflow smoothed Savitzky-Golay [l/s]'
    )

    trace3 = go.Scatter(
        x=x,
        y=y_noise,
        mode='lines',
        line=dict(
            # size=6,
            color='#5E88FC',
            # symbol='circle-open'
            shape='linear'
        ),
        # name='Noisy Sine'
        name='Pre-treated: Inflow with noise [l/s]'
    )

    trace2 = go.Scatter(
        x=x,
        y=y_raw_filled,
        mode='lines',
        line=dict(
            # size=6,
            color='#C190F0',
            # symbol='triangle-up'
            shape='linear'
        ),
        name='Pre-treated: Inflow with missing data [l/s]'
    )

    trace1 = go.Scatter(
        x=x,
        y=y_raw,
        mode='lines',
        line=dict(
            # size=6,
            color='#56ce98',
            # symbol='triangle-up'
            shape='linear'
        ),
        name='Raw: Inflow [l/s]'
    )

    layout = go.Layout(
        showlegend=True
    )

    # data = [trace1, trace2, trace3]
    data = [trace1, trace2, trace3, trace4]
    fig = go.Figure(data=data, layout=layout)
    py.iplot(fig, filename='Pumping Station Inflow', fileopt='overwrite',  auto_open=True)