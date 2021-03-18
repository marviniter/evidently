#!/usr/bin/env python
# coding: utf-8

import json
import pandas as pd

import numpy as np

from sklearn import metrics, preprocessing
from pandas.api.types import is_numeric_dtype

import plotly.graph_objs as go
import plotly.figure_factory as ff

from evidently.model.widget import BaseWidgetInfo, AlertStats, AdditionalGraphInfo
from evidently.widgets.widget import Widget

red = "#ed0400"
grey = "#4d4d4d"


class ProbClassProdMetricsMatrixWidget(Widget):
    def __init__(self, title: str):
        super().__init__()
        self.title = title

    def get_info(self) -> BaseWidgetInfo:
        #if self.wi:
        return self.wi
        #raise ValueError("No prediction or target data provided")

    def calculate(self, reference_data: pd.DataFrame, production_data: pd.DataFrame, column_mapping): 
        if column_mapping:
            date_column = column_mapping.get('datetime')
            id_column = column_mapping.get('id')
            target_column = column_mapping.get('target')
            prediction_column = column_mapping.get('prediction')
            num_feature_names = column_mapping.get('numerical_features')
            target_names = column_mapping.get('target_names')
            if num_feature_names is None:
                num_feature_names = []
            else:
                num_feature_names = [name for name in num_feature_names if is_numeric_dtype(reference_data[name])] 

            cat_feature_names = column_mapping.get('categorical_features')
            if cat_feature_names is None:
                cat_feature_names = []
            else:
                cat_feature_names = [name for name in cat_feature_names if is_numeric_dtype(reference_data[name])] 
        
        else:
            date_column = 'datetime' if 'datetime' in reference_data.columns else None
            id_column = None
            target_column = 'target' if 'target' in reference_data.columns else None
            prediction_column = 'prediction' if 'prediction' in reference_data.columns else None

            utility_columns = [date_column, id_column, target_column, prediction_column]

            num_feature_names = list(set(reference_data.select_dtypes([np.number]).columns) - set(utility_columns))
            cat_feature_names = list(set(reference_data.select_dtypes([np.object]).columns) - set(utility_columns))

            target_names = None

        if production_data is not None and target_column is not None and prediction_column is not None:
            production_data.replace([np.inf, -np.inf], np.nan, inplace=True)
            production_data.dropna(axis=0, how='any', inplace=True)

            binaraizer = preprocessing.LabelBinarizer()
            binaraizer.fit(reference_data[target_column])
            binaraized_target = binaraizer.transform(production_data[target_column])

            array_prediction = production_data[prediction_column].to_numpy()

            prediction_ids = np.argmax(array_prediction, axis=-1)
            prediction_labels = [prediction_column[x] for x in prediction_ids]

            labels = sorted(set(production_data[target_column]))
            
            #plot support bar
            metrics_matrix = metrics.classification_report(production_data[target_column], prediction_labels,
             output_dict=True)
            metrics_frame = pd.DataFrame(metrics_matrix)

            z = metrics_frame.iloc[:-1,:-3].values
            x = labels
            y =  ['precision', 'recall', 'f1-score']

            if len(prediction_column) > 2:
                roc_aucs = metrics.roc_auc_score(binaraized_target, array_prediction, average=None)
                z = np.append(z, [roc_aucs], axis = 0)
                y.append('roc-auc')

            # change each element of z to type string for annotations
            z_text = [[str(round(y,3)) for y in x] for x in z]

            # set up figure 
            fig = ff.create_annotated_heatmap(z, y=y, x=x, annotation_text=z_text, colorscale='bluered',showscale=True)
            fig.update_layout(
                xaxis_title="Class", 
                yaxis_title="Metric")

            metrics_matrix_json = json.loads(fig.to_json())

            self.wi = BaseWidgetInfo(
                title=self.title,
                type="big_graph",
                details="",
                alertStats=AlertStats(),
                alerts=[],
                alertsPosition="row",
                insights=[],
                size=1,
                params={
                    "data": metrics_matrix_json['data'],
                    "layout": metrics_matrix_json['layout']
                },
                additionalGraphs=[],
            )
        else:
            self.wi = None

