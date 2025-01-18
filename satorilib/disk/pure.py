import pandas as pd

def search(
    self,
    time: str,
    before: bool = False,
    after: bool = False,
    exact: bool = False
) -> pd.DataFrame:
    if (
        not isinstance(time, str) or
        not any([before, after, exact]) or
        self.df is None
    ):
        return None
    if before:
        return self.df[self.df.index < time]
    if after:
        return self.df[self.df.index > time]
    if exact:
        return self.df[self.df.index == time]
    return None
