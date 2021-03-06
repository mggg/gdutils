"""
gdutils.dataqa
==============

Provides
    - A ``python`` module containing data quality assurance functions.

Metadata
--------
:Module:        ``gdutils.dataqa``
:Filename:      `dataqa.py <https://github.com/mggg/gdutils/>`_
:Author:        `@KeiferC <https://github.com/keiferc>`_
:Date:          14 August 2020
:Version:       1.0.0
:Description:   Module for data quality assurance
:Dependencies:  

                - ``geopandas``
                - ``gdutils.extract``
                - ``pandas``

Documentation
-------------
Documentation for the ``dataqa`` module can be found as docstrings. 
Run ``import gdutils.dataqa; help(gdutils.dataqa)`` to view documentation.
::

    $ python
    >>> import gdutils.dataqa; help(gdutils.dataqa)

Additionally, documentation can be found on `Read the Docs 
<https://gdutils.readthedocs.io>`_.

"""
import geopandas as gpd
import json
import os
import pandas as pd 
import pathlib
import requests
import subprocess
import sys
import urllib.parse

import gdutils.extract as et
from typing import (Any, Dict, Hashable, Iterable, List, 
                    NoReturn, Optional, Set, Tuple, Union)



#########################################
#                                       #
#       Function Definitions            #
#                                       #
#########################################

def compare_column_names(table: Union[pd.DataFrame, gpd.GeoDataFrame],
                         standards: Union[List[str], Set[str]]
                         ) -> Tuple[Set[str], Set[str]]:
    """
    Given either a pandas DataFrame or a geopandas GeoDataFrame and a list
    of standardized column names, returns a tuple containing the intersection
    between standardized column names and columns in the table and the set of
    columns names in the table that are not in the standards.

    Parameters
    ----------
    table : pd.DataFrame | gpd.GeoDataFrame
        Tabular data whose column names are to be compared against the 
        standards.
    standards : List[str] | Set[str]
        List/set of standardized column names to be compared against the given
        tabular data.
    
    Returns
    -------
    Tuple[Set[str], Set[str]]
        The first set in the tuple contains the intersection of column names
        between the table and the standards list. The second set in the tuple
        contains the column name in the difference between the table and the
        standards list. E.g. ``( {'match1', 'match2'}, {'diff1'} )``.

    Examples
    --------
    >>> standards = ['COL1', 'COL2', 'COL3']
    >>> df = pd.DataFrame(data=[[1, 2, 3], [4, 5, 6]],
    ...                   columns=['COL1', 'col2', 'COL3'])
    >>> print(df)
       COL1  col2  COL3
    0     1     2     3
    1     4     5     6
    >>> (matches, discrepancies) = dataqa.compare_column_names(df, standards)
    # gets a tuple that splits DataFrame column names into two categories:
    # 1. names in the 'standards' list (left)
    # 2. names not in the 'standards' list (right)
    >>> print(matches)
    {'COL1', 'COL3'}
    >>> print(discrepancies)
    {'col2'}

    """
    intersection = set(standards).intersection(set(table.columns))
    difference = set(table.columns) - intersection
    return (intersection, difference)


def sum_column_values(table: Union[pd.DataFrame, gpd.GeoDataFrame],
                      columns: Union[List[str], Set[str]]
                      ) -> List[Tuple[str, int]]:
    """
    Given a pandas DataFrame or a geopandas GeoDataFrame, and given a list of 
    column names, returns a list of tuples of column names and the sum of 
    their values. It is an unchecked runtime error if a column containing 
    non-numerical values is passed into the function.

    Parameters
    ----------
    table : pd.DataFrame, gpd.GeoDataFrame
        Tabular data containing columns whose values are to be summed.
    columns: List[str] | Set[str]
        A list/set of column names whose values are to be summed.
    
    Returns
    -------
    List[Tuple[str, int]]
        A list of tuples of column names associated with the sum of their 
        values. E.g. ``[ ('column 1', 100), ('column 2', 53) ]``.
    
    Raises
    ------
    KeyError
        Raised if given column name does not exist in table.
    
    Examples
    --------
    >>> cols = ['COL1', 'COL3']
    >>> df = pd.DataFrame(data=[[1, 2, 3], [4, 5, 6]],
    ...                   columns=['COL1', 'COL2', 'COL3'])
    >>> print(df)
       COL1  COL2  COL3
    0     1     2     3
    1     4     5     6
    >>> totals = dataqa.sum_column_values(df, cols)
    # gets a list of tuples containing two items:
    # 1. column name (left)
    # 2. sum of column's values (right)
    >>> for total in totals:
    ...     (column, sum) = total
    ...     print("{}: {}".format(column, sum))
    COL1: 5
    COL3: 9 

    """
    return [(col, table[col].sum()) for col in list(columns)]


def compare_column_values(
        table1: Union[pd.DataFrame, gpd.GeoDataFrame],
        table2: Union[pd.DataFrame, gpd.GeoDataFrame],
        columns1: List[str], 
        columns2: List[str],
        rows1: Optional[List[Hashable]] = None,
        rows2: Optional[List[Hashable]] = None
        ) -> Dict[str, List[Tuple[Hashable, Any]]]:
    """
    Given two tables and their corresponding columns and rows to compare,
    returns a dictionary containing the compared columns and a corresponding 
    list of tuples containing row names and the differences of values.

    *Note:* The comparison is a one-to-one and onto function. I.e. Each element 
    in one given list must correspond to another element in the other list.

    Parameters
    ----------
    table1: pd.DataFrame | gpd.GeoDataFrame
        Tabular data containing column values to compare.
    table2: pd.DataFrame | gpd.GeoDataFrame
        Tabular data containing column values to compare.
    columns1: List[str]
        Columns in table1 to compare.
    columns2: List[str]
        Columns in table2 to compare.
    rows1: List[Hashable], optional, default = ``None``
        Rows in table1 to compare. AKA value(s) of table's index.
        If ``None``, function compares all rows.
    rows2: List[Hashable], optional, default = ``None``
        Rows in table2 to compare. AKA value(s) of table's index.
        If ``None``, function compares all rows.

    Returns
    -------
    Dict[str, List[Tuple[Hashable, Any]]]
        A dictionary with string keys corresponding to names of compared
        columns and with List values of tuples corresponding to names of 
        compared rows and the  differences of their values. E.g.
        ::
        
            {'c1 [vs] c2': [('row1 [vs] row1', 2), ('row2 [vs] row2', 0)],
             'cA [vs] cB': [('rowA1 [vs] rowB1', 5)]}

    Raises
    ------
    KeyError
        Raised if unable to find column or row in tables.
    TypeError
        Raised if unable to calculate the difference between
        two values.
    RuntimeError
        Raised if given lists cannot be compared.
    
    See Also
    --------
    dataqa.compare_column_sums
    
    Examples
    --------
    >>> df1 = pd.DataFrame(data=[[1, 2, 3], [4, 5, 6]],
    ...                    columns=['COL1', 'COL2', 'COL3'])
    >>> df2 = pd.DataFrame(data=[[4, 5], [1, 2]], columns=['col2', 'col1'])
    >>> results = dataqa.compare_column_values(df1, df2, ['COL3'], ['col2'])
    # gets a dictionary (collection of key-value pairs), where
    # key : name of first column and name of second column
    # value: list of tuples with two values:
    #       1. name of row in first table and name of row in second table
    #       2. difference between values in the columns and rows
    >>> print(results)
    {'COL3 [vs] col2': [('0 [vs] 0', -1), ('1 [vs] 1', 5)]}

    >>> results = dataqa.compare_column_values(df1, df2, ['COL1', 'COL2'], 
    ...                                        ['col1', 'col2'])
    # compares columns 'COL1' with 'col1' and 'COL2' with 'col2'
    >>> print(results['COL2 [vs] col2'][0])
    ('0 [vs] 0', 2)
    >>> for column in results:
    ...     print('{} ----'.format(column))
    ...     for row, difference in results[column]:
    ...         print('{} : {}'.format(row, difference))
    COL1 [vs] col1 ---
    0 [vs] 0 : -4
    1 [vs] 1 : 2
    COL2-col2 ---
    0 [vs] 0 : -2
    1 [vs] 1 : 4

    >>> results = dataqa.compare_column_values(df1, df2, ['COL1'], 
    ...                                        ['col1'], [0], [1])
    # compares value of column 'COL1' row 0 in table1 with 
    # value of column 'col1' row 1 in table2
    >>> print(results['COL1 [vs] col1'][0])
    ('0 [vs] 1', -1)

    >>> results = dataqa.compare_column_values(df1, df2, ['COL1'], ['col1'],
    ...                                        [0, 1], [1, 0])
    # compares rows 0 and 1 (table1) with rows 1 and 0 (table2) in 
    # respective columns 'COL1' and 'col1'
    >>> print(results['COL1 [vs] col1'])
    [('0 [vs] 1', -1), ('1 [vs] 0', -1)]

    """
    if not __can_compare(columns1, columns2):
        raise ValueError(
            'Cannot compare columns {} and {}.'.format(columns1, columns2))
    
    if rows1 is None and rows2 is None:
        return compare_column_values(table1, table2, columns1, columns2, 
                                     table1.index.tolist(), 
                                     table2.index.tolist())

    elif (rows1 is not None and rows2 is not None and 
          not __can_compare(rows1, rows2)):
        raise ValueError('Cannot compare rows {} and {}.'.format(rows1, rows2))

    else:
        results = {}
        for i in range(0, len(columns1)):
            diff = [('{} [vs] {}'.format(rows1[j], rows2[j]), 
                    (table1.at[rows1[j], columns1[i]] -
                     table2.at[rows2[j], columns2[i]])) 
                    for j in range(len(rows1))]
            results['{} [vs] {}'.format(columns1[i], columns2[i])] = diff
        
        return results


def compare_column_sums(
        table1: Union[pd.DataFrame, gpd.GeoDataFrame],
        table2: Union[pd.DataFrame, gpd.GeoDataFrame],
        columns1: List[str],
        columns2: List[str]
        ) -> List[Tuple[Hashable, Any]]:
    """
    Given two tables and two lists of column names corresponding to the tables,
    returns a list of tuples containing the compared column names and the 
    difference between their corresponding sums. It is an unchecked runtime 
    error if a column containing non-numerical values is passed into the 
    function.

    *Note:* The comparison is a one-to-one and onto function. I.e. each element 
    in one list of column names must correspond to another element in the other 
    list.

    Parameters
    ----------
    table1: pd.DataFrame | gpd.GeoDataFrame
        Tabular data containing column values to compare.
    table2: pd.DataFrame | gpd.GeoDataFrame
        Tabular data containing column values to compare.
    columns1: List[str]
        Column(s) in table1 to compare.
    columns2: List[str]
        Column(s) in table2 to compare.

    Returns
    -------
    List[Tuple[Hashable, Any]]
        A list containing tuples that contain a label describing the
        compared columns' names and contain the difference
        between the sum of the values of the given columns. E.g.
        ``[ ('column1A-column1B', 4), ('column2A-column2B', 53) ]``.

    Raises
    ------
    KeyError
        Raised if a given column name does not exist in a given table.
    RuntimeError
        Raised if given columns cannot be compared.
    
    See Also
    --------
    dataqa.compare_column_values

    Examples
    --------
    >>> df1 = pd.DataFrame(data=[[1, 2, 3], [4, 5, 6]],
    ...                    columns=['COL1', 'COL2', 'COL3'])
    >>> df2 = pd.DataFrame(data=[[4, 5], [1, 2]],
    ...                    columns=['col2', 'col1'])
    >>> diffs = dataqa.compare_column_sums(df1, df2, ['COL1'], ['col1'])
    # gets a list of tuples containing two values:
    # 1. name of column in first table and name of column in second (left)
    # 2. difference between the sum of values of both columns (right)
    >>> print(diffs)
    [('COL1 [vs] col1', -2)]

    >>> diffs = dataqa.compare_column_sums(df1, df2, ['COL1', 'COL3'],
    ...                                    ['col1', 'col2'])
    # compares column 'COL1' with column 'col1' and compares column
    # 'COL3' with column 'col2'
    >>> for column, difference in diffs:
    ...     print('{} : {}'.format(column, difference))
    COL1 [vs] col1 : -2
    COL3 [vs] col2 : 4

    """
    if not __can_compare(columns1, columns2):
        raise ValueError(
            'Cannot compare columns {} and {}.'.format(columns1, columns2))

    sums1 = sum_column_values(table1, columns1)
    sums2 = sum_column_values(table2, columns2)

    return list(map(lambda tup1, tup2: ('{} [vs] {}'.format(tup1[0], tup2[0]),
                                        (tup1[1] - tup2[1])), sums1, sums2))


def has_missing_geometries(gdf: gpd.GeoDataFrame,
                           threshold: Optional[float] = 0.0) -> bool:
    """
    Returns True if the given GeoDataFrame has missing geometries.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame whose geometries are to be checked.
    threshold : float, optional, default = ``0.0``
        Percentage of rows that are allowed to have missing geometries.
        e.g. ``threshold = 0.5`` means that the function returns True
        if the number of missing geometries is greater than half of the
        number of rows.

    Returns
    -------
    bool
        True if the given GeoDataFrame has missing geometries.

    Raises
    ------
    KeyError
        Raised if 'geometry' column is missing.

    See Also
    --------
    dataqa.has_empty_geometries

    Examples
    --------
    >>> from shapely.geometry import Point as Pt
    >>> gdf = gpd.GeoDataFrame({'col'       : ['v1', 'v2', 'v3'], 
    ...                         'geometry'  : [None, Pt(1, 2), Pt(2, 1)]})
    >>> print(dataqa.has_missing_geometries(gdf))
    # Check if gdf has missing geometries
    True

    >>> print(dataqa.has_missing_geometries(gdf, threshold=0.75))
    # Check if more than 75% of the rows contain missing geometries
    False

    """
    return (list(gdf['geometry'].isna()).count(True) >
            len(gdf['geometry']) * threshold)


def has_empty_geometries(gdf: gpd.GeoDataFrame,
                         threshold: Optional[float] = 0.0) -> bool:
    """
    Returns True if the given GeoDataFrame has empty geometries.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame whose geometries are to be checked.
    threshold : float, optional, default = ``0.0``
        Percentage of rows that are allowed to have empty geometries.
        e.g. ``threshold = 0.5`` means that the function returns True
        if the number of empty geometries is greater than half of the
        number of rows.

    Returns
    -------
    bool
        True if the given GeoDataFrame has empty geometries.

    Raises
    ------
    KeyError
        Raised if 'geometry' column is missing.

    See Also
    --------
    dataqa.has_missing_geometries

    Examples
    --------
    >>> from shapely.geometry import Polygon as Pg
    >>> from shapelygeometry import Point as Pt
    >>> gdf = gpd.GeoDataFrame({'col'       : ['v1', 'v2', 'v3'], 
    ...                         'geometry'  : [Pt(1, 2), Pg([]), Pt(2, 1)]})
    >>> print(dataqa.has_empty_geometries(gdf))
    # Check if gdf has empty geometries
    True

    >>> print(dataqa.has_empty_geometries(gdf, threshold=0.75))
    # Check if more than 75% of the rows contain empty geometries
    False

    """
    return (list(gdf['geometry'].is_empty).count(True) >
            len(gdf['geometry']) * threshold)



#########################################
#                                       #
#           Helper Definitions          #
#                                       #
#########################################

def __can_compare(xs: Union[Set[Hashable], List[Hashable]], 
                  ys: Union[Set[Hashable], List[Hashable]]) -> bool:
    """
    Returns ``True`` is given are both sets/lists of equal length > 0.

    """
    return (
        (xs is not None and ys is not None and isinstance(xs, type(ys)))
        and
        (not isinstance(xs, Hashable) and len(xs) > 0 and len(xs) == len(ys)))
