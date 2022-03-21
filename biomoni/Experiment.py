import numpy as np
import pandas as pd
import glob
import os.path
import warnings
from copy import deepcopy

#ELELE

class Experiment:
    """
    A class for creating an Experiment object with preprocessed datasets e.g. offline(HPLC, bio dry mass), online (MFCS), CO2(Bluesense) data. The class assumes that there is a common path (path) where the whole data and the metadata is present within.
    It is assumed that files of the same types e.g. offline are called the same in every subfolder: e.g. the offline files in F1 and F2 (two experiment days - two subfolders in path) are named "offline.csv" in both subfolders. 
    It is also asumed that the raw data from types like "offline.csv" is generated by the same device and is thus idenical and requires identical settings to read.
    It is also assumed that the Experiment names (sub folder names for experiments) are equal to the experiment names in the metadata index column in order to get the right settings.
    If that is not the case and the folder with the measurement data is named differently as the id in metadata or if the directory is not present within path, consider to use exp_dir_manual to give the directory of the measurement data.

    :param path: Path of overarching directory, the metadata.xlsx file and the directories containing the data (e.g. online, offline and CO2) must be within this directory.
    :type path: str
    :param exp_id: Identifier of the right experiment, must match with index column in metadata.
    :type exp_id: int or str
    :param meta_path: metadata file name within path.
    :type meta_path: str
    :param types: Dict with measurement data types as keys and file locations within path (or exp_dir_manual) as value.
    :type types: dict
    :param exp_dir_manual: Manually given experiment path, can be used if the experiment data is in another directory environment than in 'param path' where the metadata is, or if the data is in the same directory but the the experiment identifier (exp_id (e.g. F1) which is also the index column in metadata) does not match with the folder name, e.g. when folder name is created automatically and thus hard to give the rigth exp_id for the Folder (eg. when the Folder is named "Exp_dateX_timeX" and is created automatically).
    :type exp_dir_manual: str
    :param index_ts: Dict with measurement data types as keys and index of timestamp column in raw data as value.
    :type index_ts: None or dict with ints
    :param read_csv_settings: Dict with measurement data types as keys and pd.read_csv settings to read the correspondig raw data to a pd.DataFrame as value.
    :type read_csv_settings: None or dict with settings
    :param to_datetime_settings: Dict with measurement data types as keys and settings to convert timestamp column in raw data to pd.Timestamp as value.
    :type to_datetime_setings: None or dict with settings
    :param calc_rate: column in data frame of typ which should be derived to get the rate.
    :type calc_rate: tuple
    :param endpoint: Name of endpoint column in metadata. Helpful if you have several endpoints in your metadata.
    :type endpoint: str
    :param read_excel_settings: Settings to metadata excel file.
    :type read_excel_settings: None or dict.


    :return: Experiment object contaning the measurement data.

        """   


    def __repr__(self):
        """Representation of Experiment object in the print statement"""
        return  """Experiment(\"{path}\" , \"{exp_id}\")""".format(path= self.path, exp_id= self.exp_id)

    #format_ts kommt raus wenn du eh to_datetime_settings_gibst

    def __init__(self, path, exp_id, meta_path = "metadata.xlsx"
    , types = {"off" : "offline.csv", "on": "online.CSV", "CO2" : "CO2.dat"}
    , exp_dir_manual = None
    , index_ts = {"off" : 0, "on": 0, "CO2" : 0}

    , read_csv_settings = { "off" : dict(sep=";", encoding= 'unicode_escape', header = 0, usecols = None)
    , "on": dict(sep=";",encoding= "unicode_escape",decimal=",", skiprows=[1,2] , skipfooter=1, usecols = None, engine="python")
    , "CO2" : dict(sep=";", encoding= "unicode_escape", header = 0, skiprows=[0], usecols=[0,2,4], names =["ts","CO2", "p"])    }

    , to_datetime_settings = {"off" : dict(format = "%d.%m.%Y %H:%M", exact= False, errors = "coerce")
    , "on": dict(format = "%d.%m.%Y  %H:%M:%S", exact= False, errors = "coerce")
    , "CO2" : dict(format = "%d.%m.%Y %H:%M:%S", exact= False, errors = "coerce")   }

    , calc_rate = ("on", "BASET")
    , endpoint = "end1"
    , read_excel_settings = None

    ):
       

    # , filtering_columns = False, filter_on = ["base_rate"], filter_off = ["cX", "cS", "cE"], filter_CO2 = ["CO2"]
        pd.options.mode.chained_assignment = None       #because of pandas anoying error
        
        assert type(path) is str, "The given Path must be of type str"
        assert type(meta_path) is str, "The given meta_path must be of type str"
        assert all(isinstance(i, str) for i in types.values() ), "given file names must be strings"
       
        
        if index_ts is None:        #if no index_col is given, the timestamp column is assumed to be the first column (0) in the datafile
            index_ts = dict.fromkeys(types) #same keys as measurement types
            for typ in types.keys():
                index_ts[typ] = 0
        else: 
            assert index_ts.keys() == types.keys(), "The given type names must match with the keys of index_ts, read_csv_settings and to_datetime_settings"

        if read_csv_settings is None:
            read_csv_settings = dict.fromkeys(types)
            for typ in types.keys():
                read_csv_settings[typ] = dict(sep = ",")     #default setting from pandas read_csv, given here because it is later unkapcked with **read_csv_settings in the read_data function. I think it would also work with dict().
        else: 
            assert read_csv_settings.keys() == types.keys(), "The given type names must match with the keys of index_ts, read_csv_settings and to_datetime_settings"

        if to_datetime_settings is None:
            to_datetime_settings = dict.fromkeys(types)
            for typ in types.keys():
                to_datetime_settings[typ] = dict(errors="raise")    #standard panas.to_dattime seeting
        else: 
            assert to_datetime_settings.keys() == types.keys(), "The given type names must match with the keys of index_ts, read_csv_settings and to_datetime_settings"

        
        if read_excel_settings is None:
            read_excel_settings = dict(header = 0) #standard read_excel settings


        self.path = path 
        self.exp_id = exp_id
        self.endpoint = endpoint



        if exp_dir_manual is None:
            dir = os.path.join(path, exp_id)    #if no manual experiment name(exp_dir_manual - folder name) is given, the exp_id is assumed to be named as the subfolder within path.
            assert os.path.isdir(dir), "The directory {0} does not exist. If the experiment folder has another name as the identifier exp_id, consider to use exp_dir_manual as subfolder path name.".format(dir)
        else:
            dir = exp_dir_manual
            assert os.path.isdir(dir), "The directory {0} does not exist.".format(dir)

        file_path = {}
        for typ, filename in types.items():
            file_path[typ] = os.path.join(dir, filename)
           

        

        self.dataset = {}
        for typ, p in file_path.items():
            if os.path.isfile(p):   #checking if the file in the experiment folder even exists              #Gefährlich try except
                self.dataset[typ] = self.read_data(path = p, index_ts = index_ts[typ], read_csv_settings = read_csv_settings[typ], to_datetime_settings = to_datetime_settings[typ])
            else:
                warnings.warn("The file {0} could not be found within the Experiment folder: {1}".format(types[typ], dir))
        
        if not self.dataset: raise TypeError("No data were collected, check if measurement data is in the right directory and if it is named correctly in the 'types' argument ")

        metadata_all = pd.read_excel(os.path.join(path, meta_path), index_col = 0, **read_excel_settings)
        metadata_all = metadata_all.astype(object).where(metadata_all.notnull(), None)  #load metadata and replace NaN and NaT values with None required for adequate time filtering in time_filter
        assert exp_id in metadata_all.index.values, "Experiment have to be in metadata"
        self.metadata = metadata_all.loc[exp_id]

        
        assert endpoint in metadata_all.columns, "Given endpoint must be in metadata columns"
        start = self.metadata["start"]
        end = self.metadata[endpoint]    

        for dskey in self.dataset.keys():   
            self.calc_t(dskey = dskey, start = start)

        self.dataset_raw = deepcopy(self.dataset)   #raw dataset, may be needed if changes are made on self.dataset after the Experiment object is created. For example if the feed_rate is required for the entire time span.

        for dskey in self.dataset.keys():
            self.time_filter(dskey, start, end)
        
        if calc_rate is not None:
            self.calc_rate(*calc_rate)
        
        
    
    def time_filter(self, dskey, start = None, end = None):
        """Function to filter according to process time  

        :param dskey: Dataset key correspond to one of the measuring types (e.g. "off" , "CO2").
        :type dskey: dict key
        :param start: Timestamp of start point.
        :type start: pd.Timestamp or str
        :param end:  Timestamp of end point.
        :type end: pd.Timestamp or str
        :return: Filtered dataframes in dataset.

        """
        df = self.dataset[dskey]        # df = deepcopy(self.dataset[key] to avoid error message?) or pd.options.mode.chained_assignment = None in constructor

        start = pd.to_datetime(start)
        end = pd.to_datetime(end)

        #case distinction depening on given start and/or end time points
        if start is None:

            if end is None:
                pass
            
            elif end is not None:
                df = df[(df["ts"] <= end)]  

        elif start is not None:

            if end is None:
                df = df[(df["ts"] >= start)]  
            
            elif end is not None: 
                df = df[(df["ts"] >= start ) &  (df["ts"] <= end)] 

        self.dataset[dskey] = df



    def calc_t(self, dskey, start = None):
        """ Calculates process time as decimal number.

        :param dskey: Dataset key correspond to one of the measuring types (e.g. "off" , "CO2")
        :type dskey: dict key
        :param start: Timestamp of start point
        :type start: pd.Timestamp or str
        :return: Time as decimal number in a new column "t"
        
        """

        df = self.dataset[dskey]

        if start is None:
            df["t"] = (df["ts"] - df["ts"][0]) / pd.Timedelta(1,"h")
        if start is not None:
            df["t"] = (df["ts"] - start) / pd.Timedelta(1,"h")

    
        df.set_index("t", inplace= True, drop= True)        #set t to index of dataframe
        
        self.dataset[dskey] = df



    def calc_rate(self, dskey, col):
        """ Function to calculate the time derivative of a variable with finite differences.

        :param dskey: Dataset key correspond to one of the measuring types (e.g. "off" , "CO2")
        :type dskey: dict key
        :param col: Column in dataframe = variable for calculating the rate
        :type col: str
        :return: New column in dataframe named col_rate = time derivative of col.

        """

        df = self.dataset[dskey]

        try:
            df[col + "_rate"] = df[col].diff() / np.diff(df.index, prepend= 1)
        
        except:
            df[col] = pd.to_numeric(df[col] , downcast="float" , errors="coerce") # some values in BASET were recognized as string
            df[col + "_rate"] = df[col].diff() / np.diff(df.index, prepend= 1)

        self.dataset[dskey] = df

        
    def read_data(self, path, index_ts, read_csv_settings, to_datetime_settings):
        """ Function to read the measurement data with the corresponding settings

        :param path: Path of the measurement data.
        :type path: str 
        :param index_ts: Index of the timestamp column
        :type index_ts: int
        :param read_csv_settings: Pandas read_csv setings for this type of data.
        :type read_csv_settings: dict
        :param to_datetime_settings: Pandas to_datetime settings to convert timestamp column to pd.Timestamp
        :type to_datetime_settings: dict
path
        """

        df = pd.read_csv(path, **read_csv_settings)
        df["ts"] = pd.to_datetime(df.iloc[:, index_ts], **to_datetime_settings)
        return df


    def pop_dataframe(self, types):
        """Function to delete whole dataframes from the dataset, either of one or several types.

            :param types: Type of the measurement data.
            :type types: str or list of str's
            :return: Dataset without specific selected dataframe/s.
        """

        if type(types) is list:
            for typ in types:
                if typ in self.dataset.keys():
                    self.dataset.pop(typ)
                    
                else: 
                    raise ValueError("Given types must be in the dataset")

        elif type(types) is str:
            if types in self.dataset.keys():
                self.dataset.pop(types)

            else:
                raise ValueError("Typ must be in the dataset")
        else:
            raise TypeError("Type of types must be a str or a list of strings")


