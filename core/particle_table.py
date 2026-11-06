"""
Lightweight, zero-dependency tabular data container.
Replaces heavy pandas DataFrame for particle analysis results,
reducing bundle size by >50 MB and ensuring instant startup times.
"""

from typing import List, Dict, Any, Optional, Iterator, Tuple, Union
import csv
import numpy as np


class ColumnSeries:
    """Lightweight 1D series wrapping a NumPy array with aggregation methods."""

    def __init__(self, data: Union[List, np.ndarray], name: str = ""):
        self.name = name
        if isinstance(data, np.ndarray):
            self._arr = data
        else:
            self._arr = np.array(data)

    def mean(self) -> float:
        if len(self._arr) == 0:
            return 0.0
        return float(np.mean(self._arr))

    def std(self) -> float:
        if len(self._arr) <= 1:
            return 0.0
        return float(np.std(self._arr, ddof=1))

    def min(self) -> float:
        if len(self._arr) == 0:
            return 0.0
        return float(np.min(self._arr))

    def max(self) -> float:
        if len(self._arr) == 0:
            return 0.0
        return float(np.max(self._arr))

    def median(self) -> float:
        if len(self._arr) == 0:
            return 0.0
        return float(np.median(self._arr))

    def sum(self) -> float:
        if len(self._arr) == 0:
            return 0.0
        return float(np.sum(self._arr))

    def tolist(self) -> List[Any]:
        return self._arr.tolist()

    @property
    def values(self) -> np.ndarray:
        return self._arr

    def __len__(self) -> int:
        return len(self._arr)

    def __getitem__(self, idx: Union[int, slice, np.ndarray]):
        if isinstance(idx, (slice, np.ndarray)):
            return ColumnSeries(self._arr[idx], self.name)
        return self._arr[idx]

    def __iter__(self):
        return iter(self._arr)

    def __repr__(self) -> str:
        return f"ColumnSeries({self.name}, count={len(self._arr)})"


class _ILocIndexer:
    """Helper for pandas-compatible .iloc indexing."""

    def __init__(self, table: 'ParticleTable'):
        self._table = table

    def __getitem__(self, idx: Union[int, slice]):
        if isinstance(idx, int):
            return self._table._rows[idx]
        if isinstance(idx, slice):
            new_table = ParticleTable()
            new_table._columns = list(self._table._columns)
            new_table._rows = self._table._rows[idx]
            return new_table
        raise TypeError(f"Invalid index type for iloc: {type(idx)}")


class ParticleTable:
    """
    Lightweight 2D Table structure matching pandas.DataFrame API used across PyImageJ:
    - .columns
    - len(table)
    - table[col_name] -> ColumnSeries (.mean(), .std(), .min(), .max(), .median(), .sum(), .tolist())
    - table.iloc[i] -> row dict
    - table.iterrows() -> (index, row_dict)
    - table.head(n)
    - table.sort_values(by, ascending)
    - table.to_csv(filepath, index=False)
    - table.to_dict(orient="records")
    """

    def __init__(self, data: Optional[Union[List[Dict[str, Any]], Dict[str, List[Any]], 'ParticleTable']] = None, columns: Optional[List[str]] = None):
        self._columns: List[str] = []
        self._rows: List[Dict[str, Any]] = []

        if data is None:
            if columns:
                self._columns = list(columns)
            return

        if isinstance(data, ParticleTable):
            self._columns = list(data._columns)
            self._rows = [dict(r) for r in data._rows]
            return

        if isinstance(data, list):
            self._rows = data
            if columns is not None:
                self._columns = list(columns)
            elif len(data) > 0 and isinstance(data[0], dict):
                self._columns = list(data[0].keys())
        elif isinstance(data, dict):
            # Dict of lists
            keys = list(data.keys())
            self._columns = keys
            n_rows = len(data[keys[0]]) if keys else 0
            self._rows = []
            for i in range(n_rows):
                self._rows.append({k: data[k][i] for k in keys})
        else:
            raise TypeError(f"Unsupported data type for ParticleTable: {type(data)}")

    @property
    def columns(self) -> List[str]:
        return list(self._columns)

    @property
    def empty(self) -> bool:
        return len(self._rows) == 0

    @property
    def iloc(self) -> '_ILocIndexer':
        return _ILocIndexer(self)

    @property
    def loc(self) -> '_ILocIndexer':
        return _ILocIndexer(self)

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, key: Union[str, int, slice]) -> Any:
        if isinstance(key, str):
            if key not in self._columns:
                raise KeyError(f"Column '{key}' not in table")
            col_vals = [r.get(key, None) for r in self._rows]
            # Try float/int array if numeric
            try:
                arr = np.array(col_vals, dtype=np.float64)
            except (ValueError, TypeError):
                arr = np.array(col_vals, dtype=object)
            return ColumnSeries(arr, name=key)

        if isinstance(key, int):
            return self._rows[key]

        if isinstance(key, slice):
            new_table = ParticleTable()
            new_table._columns = list(self._columns)
            new_table._rows = self._rows[key]
            return new_table

        raise TypeError(f"Invalid key type: {type(key)}")

    def __setitem__(self, key: str, value: Any):
        if key not in self._columns:
            self._columns.append(key)
        if hasattr(value, "__len__") and len(value) == len(self._rows):
            for i, val in enumerate(value):
                self._rows[i][key] = val
        else:
            for r in self._rows:
                r[key] = value

    def iterrows(self) -> Iterator[Tuple[int, Dict[str, Any]]]:
        for i, row in enumerate(self._rows):
            yield i, row

    def head(self, n: int = 5) -> 'ParticleTable':
        new_table = ParticleTable()
        new_table._columns = list(self._columns)
        new_table._rows = self._rows[:n]
        return new_table

    def sort_values(self, by: str, ascending: bool = True) -> 'ParticleTable':
        if by not in self._columns:
            raise KeyError(f"Column '{by}' not in table")
        sorted_rows = sorted(
            self._rows,
            key=lambda r: (r.get(by) is None, r.get(by, 0)),
            reverse=not ascending
        )
        new_table = ParticleTable()
        new_table._columns = list(self._columns)
        new_table._rows = sorted_rows
        return new_table

    def to_dict(self, orient: str = "records") -> List[Dict[str, Any]]:
        return [dict(r) for r in self._rows]

    def to_csv(self, filepath: str, index: bool = False, encoding: str = "utf-8"):
        with open(filepath, mode="w", newline="", encoding=encoding) as f:
            writer = csv.writer(f)
            header = list(self._columns)
            if index:
                header = ["Index"] + header
            writer.writerow(header)

            for i, row in enumerate(self._rows):
                line = [row.get(c, "") for c in self._columns]
                if index:
                    line = [i] + line
                writer.writerow(line)

    def to_excel(self, filepath: str, index: bool = False):
        """Saves as CSV if openpyxl not installed, or attempts openpyxl."""
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            header = list(self._columns)
            if index:
                header = ["Index"] + header
            ws.append(header)
            for i, row in enumerate(self._rows):
                line = [row.get(c, "") for c in self._columns]
                if index:
                    line = [i] + line
                ws.append(line)
            wb.save(filepath)
        except ImportError:
            # Fallback to CSV
            csv_path = filepath if filepath.endswith(".csv") else filepath + ".csv"
            self.to_csv(csv_path, index=index)

    def __repr__(self) -> str:
        return f"<ParticleTable: {len(self._rows)} rows x {len(self._columns)} columns>"


# Type alias so existing code expecting DataFrame works transparently
DataFrame = ParticleTable
