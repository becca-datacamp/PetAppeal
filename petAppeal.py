import json
import sys
import urllib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import pickle
import string
import re
from textblob import TextBlob
import itertools
from sklearn.metrics import roc_curve, auc
from sklearn.utils import resample
import math
import squarify


def shelterFinder(zipcode, petFinder_api_key):
    '''
        Calls the petfinder API shelter.find method to get animal shelter info.
        
        See https://www.petfinder.com/developers/api-docs for more info.
        
        Args:
            zipcode (str): A US or Canadian ZIP code.
            petfinder_api_key (str): API key requested from Petfinder.

        Returns:
            shelters (DataFrame): A dataframe with detailed shelter information
    '''
    
    url = 'http://api.petfinder.com/shelter.find?key='+petFinder_api_key+\
    '&location='+zipcode+'&format=json'
    
    try:
        json_obj = urllib.urlopen(url)
        data = json.load(json_obj)

        individual_shelters = data['petfinder']['shelters']['shelter']
        
        shelter_vars = ['address1', 'address2', 'city', 'country', 'email',
                        'fax', 'id', 'phone', 'latitude', 'longitude', 'name',
                        'state', 'zip']
        
        shelters = pd.DataFrame(index =range(0,len(individual_shelters)),
                                columns=shelter_vars)
 
        for i in range(len(individual_shelters)):
            shelter_info = individual_shelters[i]
            for j in shelter_vars:

                try:
                    val = shelter_info[j]['$t'].encode("utf-8")
                except:
                    val = np.nan
                    
                shelters.ix[i,j]=val
                    
    except:
        print "Oops!",sys.exc_info(),\
        "occured.\nThere appear to be no animal shelters in this zip code"
    
    return shelters


def getPets(shelter_id, petFinder_api_key, status):
    '''
        Calls the petfinder API shelter.getPets method to get pet info.
    
        See https://www.petfinder.com/developers/api-docs for more info.
        
        Args:
            shelter_id (str): A Petfinder specific ID.
            petfinder_api_key (str): API key requested from Petfinder.

        Returns:
            pets (DataFrame): A dataframe with detailed pet information
    '''
        
    url = 'http://api.petfinder.com/shelter.getPets?key='+petFinder_api_key+\
    '&id='+shelter_id+'&status='+status+'&format=json&count=1000&output=full'

    pet_vars = ['age', 'animal', 'breeds', 'description', 'id', 'contact',
                    'lastUpdate', 'media', 'mix', 'name', 'options', 'sex',
                    'shelterId', 'shelterPetId', 'size', 'status']
        
    shelter_vars = ['address1', 'address2', 'city', 'email', 'fax',
                        'phone', 'state', 'zip']
        
    pets = pd.DataFrame(columns=pet_vars+shelter_vars)

    try:
        json_obj = urllib.urlopen(url)
        data = json.load(json_obj)
        
        individual_pets = data['petfinder']['pets']['pet']
        
        if type(individual_pets)==dict:
            copy = individual_pets
            individual_pets = []
            individual_pets.append(copy)
        
        pet_vars = ['age', 'animal', 'breeds', 'description', 'id', 'contact',
                    'lastUpdate', 'media', 'mix', 'name', 'options', 'sex',
                    'shelterId', 'shelterPetId', 'size', 'status']
        
        shelter_vars = ['address1', 'address2', 'city', 'email', 'fax',
                        'phone', 'state', 'zip']
        
        pets = pets.reindex(index=range(len(individual_pets)))
        
        for i in range(len(individual_pets)):
            pet_info = individual_pets[i] 
            for j in pet_vars:
                
                try:
                   val = pet_info[j]['$t'].encode("utf-8")
                except:
                    val = np.nan
                    
                if j=='breeds':                    
                    try:
                        val_main = pet_info['breeds']['breed']
                        val = []
                        for k in range(len(val_main)):
                            val.append(val_main[k]['$t'].encode("utf-8"))
                    except:
                        val = np.nan
                        
                elif j=='contact':
                    try:
                        val_main = pet_info['contact']
                        for k in shelter_vars:
                            try:
                                val = val_main[k]['$t'].encode("utf-8")
                            except:
                                val = np.nan
                            pets.ix[i,k]=val
                    except:
                        val = np.nan
                        
                elif j=='media':
                    try:
                        val_main = pet_info['media']['photos']['photo']
                        val = []
                        for k in range(len(val_main)):
                            val.append(val_main[k]['$t'].encode("utf-8"))
                    except:
                        val = np.nan
                    
                elif j=='options':
                    try:
                        val_main = pet_info['options']['option']
                        val = []
                        for k in range(len(val_main)):
                            val.append(val_main[k]['$t'].encode("utf-8"))
                    except:
                        val = np.nan
                        
                pets.ix[i,j]=val
                del val
        
                
    except:
        print "Oops!",sys.exc_info(),\
        "occured.\nThere appear to be no animals at", shelter_id
        
    rename_cols = {'breeds': 'breed', 'shelterId': 'shelter_id',
                       'media': 'photos', 'shelterPetId': 'pet_id'}
    pets.rename(columns=rename_cols,
                inplace=True)
    pets = pets.drop(labels='contact',
                     axis=1)
    
    return pets


def sort_options(options_col):
    '''
        Sorts through the options column provided by the petfinder API and 
        returns either a yes or a no if the animal meets that condition.
    
        Args:
            options_col (Series): Each row of the column contains a string
                with the 'options' for that animal

        Returns:
            options (DataFrame): A dataframe containing a column for each option
                and either a 'yes' or a 'no' if that option/condition is met
                for the given animal is returned.
    '''
    
    options_list = ['altered', 'hasShots', 'housetrained', 'noKids', 'noCats',
               'noDogs', 'noClaws', 'specialNeeds']
    
    options =pd.DataFrame(index=range(0, len(options_col)),
                          columns=options_list)
    
    for i in range(len(options_col)):
        for k in options_list:
            options_str = str(options_col[i])
            test = str(k) in options_str
            
            if test == True:
                val='yes'
            else:
                val='no'
            
            options.ix[i,k]=val
            
    return options


def description_analysis(description_col):
    '''
        Runs the animal description through sentiment analysis quantifies the 
        number of words.
    
        Args:
            description_col (Series): Each row of the column contains a string
                of the animal description.
        Returns:
            description (DataFrame): The word count (int), polarity (int), 
                subjectivity (int), and a categorical feature, description
                exists, which returns either a 'yes' or a 'no' if the
                description is empty or not.
    '''

    num_words = []
    description_polarity = []
    description_subjectivity = []
    description_exists = []

    for i in range(len(description_col)):
        
        line = str(description_col[i]).replace('nan', '')
        num_words.append(len(re.findall(r'\w+', line)))
        
        if num_words[i]==0:
            description_exists.append('no')
        else:
            description_exists.append('yes')
            
        try:
            opinion = TextBlob(line)
            polarity, subjectivity = opinion.sentiment
            description_polarity.append(polarity)
            description_subjectivity.append(subjectivity)
        except:
            description_polarity.append(0.0)
            description_subjectivity.append(0.5)
           
    description = pd.DataFrame({'description_length': num_words, 
                                'description_polarity': description_polarity, 
                                'description_subjectivity': description_subjectivity, 
                                'description_exists': description_exists})
    
    return description


def multi_adoption(name_col):
    '''
        Checks the name column for potential multiple adoptions.
        
        Args:
            name_col (Series): Each row of the column contains a string of the
                animals' name(s).
        Returns:
            multi_adoption (DataFrame): A categorical variable is returned with
                either a 'yes' or a 'no' is the name string contains words that
                suggest a multiple adoption.
    '''
            
    stopwords = ['adopts', 'neutered',"trn'd",'tnr', 'shots', 'spayed', '#',
                 'petsmart', 'pend', 'pendg','pendin', 'pending', 'hold',
                 'shelter', 'foster', 'adoption', 'reduced', 'fee', 'adopted',
                 'care', 'in', 'kitten', 'cat', 'dog', 'puppy', 'pup', 'litter']
    
    name_num = []
    name = []
    multi_animal_adoption = []
    multi_adoption_parameters = ['and', 'with', 'two', 'three']
    
    for i in range(len(name_col)):
        line = str(name_col[i])
        line = ''.join([j for j in line if not j.isdigit()])
        line = line.replace('&', 'and')
        line = line.translate(None, string.punctuation)
        line = ' '.join( [w for w in line.split() if len(w)>1] )
        line = line.lower()
        for k in range(len(stopwords)):
            line = line.replace(stopwords[k], '')
        name.append(line)
        name_num.append(len(re.findall(r'\w+', line)))
        multi_pet_potential = 0
        for j in range(len(multi_adoption_parameters)):
            test = multi_adoption_parameters[j] in line
            if test==True:
                multi = 1
            else:
                multi = 0
                
        multi_pet_potential = np.vstack([multi_pet_potential,
                                         multi])
        multi_pet_potential = multi_pet_potential.sum()
        if multi_pet_potential>0:
            multi_animal_adoption.append('yes')
        else:
            multi_animal_adoption.append('no')
    
    multi_adoption = pd.DataFrame({'multi_adoption': multi_animal_adoption})
    
    return multi_adoption


def image_analysis(image_col):
    '''
        Currently only determines whether photos have been uploaded.
    
        Args:
            image_col (Series): Each column contains a list of strings with the
                url of a pet image.
        Returns:
            image (DataFrame): A categorical variable is returned with either a 
                'yes' or a 'no' if the list either contains images or is empty.
    '''
            
    image_exists = []
    
    for i in range(len(image_col)):
        
        line = str(image_col[i]).replace('nan','')
    
        if not line:
            image_exists.append('no')
        else:
            image_exists.append('yes')
    
    image = pd.DataFrame({'image_exists': image_exists})
    
    return image

####Data visualizations customized to the Petfinder color scheme

def my_autopct(pct):
    '''
        Determines the percentage of each variable in the total dataset
    
        Args:
            pct (): The percentage of each quantity for the specified variable.
        Returns:
            pct (): Returns only the percentages that are at least 
                10% of the data
    '''
    
    return ('%.1f%%' % pct) if pct > 10 else ''
    
def piePlot(data, labels, title):
    '''
        Creates a pie plots with a bright color scheme.
    
        Args:
            data (Series): A series with the categories as the index and
                the quantity as the value.
            labels (object): An array of the categories for the specific
                feature to be plotted.
            title (str): A string of the plot title.
        Returns:
            plt
    '''
            
    colors = ['#820fdf', '#0bc7ff', '#f8685f', '#f1b82d', '#df0fd9', '#0fdf35', 
              '#f17e24', '#244ff1']
    fig = plt.figure()
    fig = plt.gcf() # get current figure
    fig.set_size_inches(8, 5)
    mpl.rcParams['font.size'] = 15.0
    plt.pie(data, 
            colors=colors, 
            autopct=my_autopct,
            startangle=140,
            pctdistance=0.5,
            labeldistance=1.0)
   
    plt.legend(loc='upper left',
               labels=labels,
               frameon=False,
               bbox_to_anchor=(0.85,1.025))
    plt.axis('equal')
    plt.title(title.upper())
    plt.tight_layout()
    plt.show()
    fname = title+'.png'
    fig.savefig(fname,
                transparent=False)
    plt.close()
    
    return plt
    
def saveVar(variable, file_name):
    '''
        Pickles a variable
        
        Args:
            variable (): The variable to be saved.
            file_name (str): The string that the pickled variable will be
                saved as.
        Returns:
            file_name.pickle: A pickle file of the variable.
    '''
    
    with open(file_name+'.pickle',"wb") as f:
        pickle.dump(variable, f)

def plotROC(y_test, y_pred_prob, model_str):
    '''
        Plots a ROC curve.
        
        Args:
            y_test (int64): An array of the test set class labels.
            y_pred_prob (float64): An array of the prediction probabilities.
            model_str (str): The name of the model (e.g., Random Forest,
                      Decision Tree, etc.)
        Returns:
            plt
    '''
    
    fpr, tpr, _ = roc_curve(y_test,
                            y_pred_prob)
    roc_auc=auc(fpr,
                tpr)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.plot(fpr,
             tpr,
             label='AUC=%0.2f'% roc_auc,
             color='#0bc7ff',
             linewidth=2.0)
    
    plt.ylabel('True Positive Rate',
               fontsize=(18),
               color='white')
    
    plt.xlabel('False Positive Rate',
               fontsize=(18),
               color='white')
    
    plt.tick_params(axis='both',
                    which='both'
                    , labelsize=14,
                    color='white')
    
    plt.title('ROC Curve',
              fontsize=(18),
              color='white',
              fontweight='bold')
    
    leg = plt.legend(framealpha = 0,
                     loc = 'lower right',
                     fontsize=(14),
                     frameon=False)
    for text in leg.get_texts():
        plt.setp(text, color = 'w')
    plt.plot([0,1],[0,1],
             color='#f1b82d',
             linestyle='--',
             linewidth=2.0)
    axes = plt.gca()
    axes.set_xlim([0,1])
    axes.set_ylim([0,1])
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_color('white')
    ax.spines['right'].set_visible(False)
    ax.xaxis.label.set_color('white')
    ax.tick_params(axis='both',
                   colors='white')
    plt.tight_layout()
    plt.show()
    fname = model_str+' ROC Curve.png'
    fig.savefig(fname,
                transparent=False)
    plt.close()
    
    return plt
    
def plot_confusion_matrix(cm, classes, normalize=False, title='Confusion matrix'):
    '''
        This function prints and plots the confusion matrix.
        Normalization can be applied by setting `normalize=True`.
        
        Args:
            cm (int64): An int array created by the sklearn.metrics 
                confusion_matrix function.
            classes (object): An object array containing the class labels.
            normalize (Boolean): True plots normalized confusion matrix.
            title (str): A string with the title for the plot.
        Returns:
            plt
    '''
    
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)
    fig = plt.figure()
    fname = title +'.png'
    plt.imshow(cm,
               interpolation='nearest',
               cmap=plt.cm.Purples)
    plt.title(title,
              fontsize=(18),
              fontweight='bold')
    cbar = plt.colorbar()
    cbar.ax.tick_params(labelsize=14)
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks,
               classes,
               rotation=0,
               fontsize=(14))
    plt.yticks(tick_marks,
               classes,
               fontsize=(14))

    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j,
                 i,
                 format(cm[i, j], fmt),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    
    plt.ylabel('True label',
               fontsize=(18),
               fontweight='bold')
    plt.xlabel('Predicted label',
               fontsize=(18),
               fontweight='bold')
    plt.tight_layout()
    plt.show()
    fname = title+'.png'
    fig.savefig(fname,
                transparent=False)
    plt.close()
    
    return plt
    

def horizontal_bar(data, title):
    '''
        Creates a horizontal bar chart.
        
        Args:
            data (float64): Dataset to plot in the form of a NumPy array.
            title (str): A string with the plot title
        Returns:
            plt
    '''
       
    #np.random.seed(19680801)
    plt.rcdefaults()
    fig, ax = plt.subplots()
    fig = plt.figure(1)

    plt.tick_params(axis='both',
                    which='major',
                    labelsize=14)
    status = ('Available', 'Adopted')
    y_pos = np.arange(len(status))
    colors = ['#f8685f', '#f1b82d']
    ax.barh(y_pos,
            data,
            color=colors,
            ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(status,
                       fontsize=(18))
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Count',
                  fontsize=(18))
    xmax = (max(data)/ 100.0) * 100+100
    ax.set_xlim([0, xmax])
    plt.tight_layout()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.show()
    fname = title+'.png'
    fig.savefig(fname,
                transparent=False)
    plt.close()
    
    return plt
    
def plot_feature_importance(x_train, importances, features, color):
    '''
        Plots the feature importances as a horizontal bar graph in
        descending order of importance
        
        Args:
            x_train (float64): The encoded training set.
            importances (float64): An array the length of the feature set with
                the numerical (0-1) level of importance.
            features (list): A list containing a string of each feature.
            color (str): The desired font color; either white or black.
        Returns:
            plt
    '''
    
    indices = np.argsort(importances)[::-1]
    arr1 = indices
    arr2 = np.array(features) #featureHeaders is the name of my list of features
    sorted_arr2 = arr2[arr1[::1]]
    
    print("Feature ranking:")

    for f in range(x_train.shape[1]):
      print("%d. %s (%f)" % (f + 1, sorted_arr2[f], importances[indices[f]]))
    
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.barh(range(x_train.shape[1]), importances[indices], color="#f1b82d")
    if color=='white':
        plt.title("Feature Importance",
                  fontsize=(22),
                  fontweight='bold',
                  color='white')
        ax.invert_yaxis()
        ax.spines['bottom'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_visible(False)
        plt.yticks(range(x_train.shape[1]), sorted_arr2, ha='right')
        plt.tick_params(axis='both',
                        which='both',
                        labelsize=14,
                        color='white')
        ax.tick_params(axis='both',
                       colors='white')
    else:
        plt.title("Feature Importance",
                  fontsize=(22),
                  fontweight='bold')
        ax.invert_yaxis()
        ax.spines['bottom'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_visible(False)
        plt.yticks(range(x_train.shape[1]), sorted_arr2, ha='right')
        plt.tick_params(axis='both',
                        which='both',
                        labelsize=14)
        
    plt.gcf().set_size_inches(8,8)
    plt.tight_layout()
    ax.grid(False)
    plt.show()
    fig.savefig('Feature Importance',
                transparent=False)
    plt.close()
    
    return plt
    
def group_bar_graph(df, labels, feature):
    '''
        Create a vertical grouped bar graph to view each feature by status.
        
        Args:
            df (DataFrame): A subset of the full feature set containing only 
                the categorical variables.
            labels (list): An ordered list of the categories for the specified
                feature.
            feature (str): The name of the feature to be plotted.
        Returns:
            plt
    '''

    pos = list(range(len(df)))
    width = 0.25 
    
    # Plotting the bars
    fig, ax = plt.subplots(figsize=(10,5))
    
    plt.bar(pos, 
            df[labels[0]], 
            width,
            color='#f8685f', 
            label=df[feature][0]) 
    
    plt.bar([p + width for p in pos], 
            df[labels[1]],
            width, 
            color='#f1b82d', 
            label=df[feature][1]) 
    ax.set_ylabel('Count')
    ax.set_facecolor('white')
    ax.set_title(feature)
    ax.set_xticks([p + 1.5 * width for p in pos])
    ax.set_xticklabels(df[feature],
                       rotation=45)
    ax.grid(False)
    plt.xlim(min(pos)-width, max(pos)+width*4)
    y_max = int(math.ceil(max(df[labels[0]].max(), df[labels[1]].max()) / 100.0)) * 100+100
    plt.ylim([0, y_max] )
    plt.legend(labels,
               loc='upper left', 
               frameon=False)
    fname = feature+'.png'
    fig.savefig(fname,
                transparent=False)
    plt.close()
    
    return plt
    
def encode_data(df):
    '''
        Encodes the data into the appropriate format for running through 
        machine learning models.
        
        Args:
            df (DataFrame): The entire (clean) feature set.
        Returns:
            df (DataFrame): An encoded feature set.
    '''
    
    ###determine is column consits of yes/no, run through loop/comprehension?
    yes_no = ['yes', 'no']
    df.multi_adoption = df['multi_adoption'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.mix = df['mix'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.altered = df['altered'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.hasShots = df['hasShots'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.housetrained = df['housetrained'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.noCats= df['noCats'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.noClaws = df['noClaws'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.noDogs = df['noDogs'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.noKids = df['noKids'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.specialNeeds = df['specialNeeds'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.description_exists = df['description_exists'].astype("category", ordered=True, categories=yes_no).cat.codes
    df.image_exists = df['image_exists'].astype("category", ordered=True, categories=yes_no).cat.codes
    
    sex = ['M', 'F', 'U']
    df.sex = df['sex'].astype("category", ordered=True, categories=sex).cat.codes
    
    animal = ['Cat', 'Dog']
    df.animal = df['animal'].astype("category", ordered=True, categories=animal).cat.codes
    
    age_ordered = ['Baby', 'Young', 'Adult', 'Senior']
    df.age = df['age'].astype("category", ordered=True, categories=age_ordered).cat.codes
    
    size_ordered = ['S', 'M', 'L', 'XL']
    df.size = df['size'].astype("category", ordered=True, categories=size_ordered).cat.codes
    
    return df


def balance_check(df, label):
    '''
        Checks the (two-class) for imbalance issues
        Downsamples the data if the imbalance exceeds a certain threshold
        Returns either the same df (if below threshold) or the class balanced df
        
        Args:
            df (DataFrame): The entire feature set, including class labels.
            label (str): The name of the class label column.
        Returns:
            df (DataFrame): The entire feature set; either unchanged, or 
                downsampled if the class imbalance exceeds 1:4 or 4:1.
    '''
    
    balance_check = df.groupby(label).size()
    balance_ratio = float(balance_check[0])/float(balance_check[1])
    
    if balance_ratio>1.6 or balance_ratio<0.6:
        
        labels = balance_check.index.values
        piePlot(balance_check,
                labels,
                'Status - Imbalanced')
        
        group1 = df[(df[label]== balance_check.index[0])]
        group2 = df[(df[label]== balance_check.index[1])]
        
        if balance_ratio>1.6:
            group1 = resample(group1,
                              n_samples=len(group2))
        else:
            group2 = resample(group2,
                              n_samples=len(group1))
            
        df = group1.append(group2)
        
        balance_check = df.groupby(label).size()
        piePlot(balance_check,
                labels,
                'Status - Balanced')
        
    return df

def plot_hist(data1, data2, feature, units):
    '''
        Plots the distribution(s) of the numerical variables by status
        
        Args:
            data1 (Series): The dataset for the first class.
            data2 (Series): The dataset for the second class.
            feature (str): The feature displayed on the histogram;
                            used for the title
            units (str): The units of the feature; used for the x label.
        Returns:
            plt: A histogram with the distributions for both dataset 1
                    and dataset 2 on top of one another.
    '''
    
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.hist(data1,
             bins='auto',
             facecolor='#f8685f')
    plt.hist(data2,
             bins='auto',
             facecolor='#f1b82d',
             alpha=0.5)
    plt.title(feature.upper(),
              fontdict= {'fontsize': 20,
               'fontweight': 'bold'})
    plt.legend(loc='upper right',
               frameon=False,
               prop={'size': 16})
    ax.set_ylabel('Count',
                  fontsize=(18))
    ax.set_xlabel(units,
                  fontsize=(18))
    ax.grid(False)
    ax.set_facecolor('white')
    plt.tick_params(axis='both',
                    which='both',
                    labelsize=14)
    plt.legend(['Adopted', 'Available'],
               loc='best', 
               frameon=False,
               fontsize=14)
    plt.show()
    fname = feature+'.png'
    fig.savefig(fname,
                transparent=False)
    plt.close()
    
    return plt
    
    
def unique_breeds(breed_col):
    '''
        Runs through the column of breeds, removes stop words 
        (i.e., coat colors), and identifies and quantifies unqiue breeds.
        Args:
            breed_col (Series): Each row contains a string with the breed of 
                the animal.
        Returns:
            breeds (Series): The series contains the unique breeds as an index 
                and the quantity of that breed as the value.
    '''
    
    coat_colors = ['Yellow', 'Chocolate', 'Black', 'Tan']
    
    breeds = breed_col.dropna()
    breeds = [i.split(',') for i in breeds]
    breeds = [item for sublist in breeds for item in sublist]
    
    breeds = [i.split('/') for i in breeds]
    breeds = [item for sublist in breeds for item in sublist]
    
    breeds = [item.translate(None, string.punctuation).strip() for item in breeds]
    breeds = [re.sub("\((.*?)\)",'', i) for i in breeds]
    
    for color in coat_colors:
        breeds = [re.sub(color,'', i).strip() for i in breeds]
    
    breeds = pd.Series(breeds,
                       name='count')
    breeds = breeds.groupby(breeds).count()
    
    return breeds

def plot_treemap(breed_col, animal_type):
    '''
        Creates a treemap of the breeds for each animal type. The large the
        quantity of a given breed, the larger the box.
        Args:
            breed_col (Series): The series contains the breeds as an index and
                the quantity of that breed as the value for the given i.
            animal_type (str): The animal type plotted (e.g., cat, dog, etc.)
        Returns:
            plt
    '''
    
    colors = ['#820fdf', '#0bc7ff', '#f8685f', '#f1b82d', '#df0fd9', '#0fdf35', 
              '#f17e24', '#244ff1']
    fig = plt.figure()
    
    labels= [breed_col.index[i]+' ('+str(breed_col[i])+')' for i in range(len(breed_col))]   
    squarify.plot(sizes=breed_col,
                  label=labels,
                  color=colors,
                  alpha=.4)
    plt.axis('off')
    plt.rc('font',
           size=10)
    plt.title(animal_type)
    plt.show()
    fname = animal_type+'_treemap.png'
    fig.savefig(fname,
                transparent=False)
    plt.close()
    
    return plt