import numpy as np
import pandas as pd
import pytest

from preprocessy.exceptions import ArgumentsError
from preprocessy.pipelines import Pipeline
from preprocessy.pipelines.config import save_config
from preprocessy.utils import num_of_samples


def custom_read(params):
    params["df"] = pd.read_csv(params["df_path"])
    params["df_copy"] = params["df"].copy()


def times_two(params):
    params["df"][params["col_1"]] *= 2


def squared(params):
    params["df"][params["col_2"]] **= 2


def split(params):
    n_samples = num_of_samples(params["df"])
    params["X_test"] = params["df"].iloc[
        : int(params["test_size"] * n_samples)
    ]
    params["X_train"] = params["df"].iloc[
        int(params["test_size"] * n_samples) :
    ]


@pytest.mark.parametrize(
    "error, df_path, steps, config_file, params, custom_reader",
    [
        (ArgumentsError, None, None, None, None, None),
        (
            ArgumentsError,
            None,
            [custom_read, times_two, squared, split],
            None,
            None,
            None,
        ),
        (
            TypeError,
            "./datasets/configs/dataset.csv",
            [custom_read, "times_two", squared, split],
            None,
            ["hello"],
            None,
        ),
        (
            TypeError,
            "./datasets/configs/dataset.csv",
            [custom_read, times_two, squared, split],
            None,
            ["hello"],
            None,
        ),
        (
            TypeError,
            "./datasets/configs/dataset.csv",
            [times_two, squared, split],
            None,
            {"col_1": "A"},
            "custom_read",
        ),
    ],
)
def test_pipeline_arguments(
    error, df_path, steps, config_file, params, custom_reader
):

    with pytest.raises(error):
        Pipeline(
            df_path=df_path,
            steps=steps,
            config_file=config_file,
            params=params,
            custom_reader=custom_reader,
        )


def test_pipeline_with_default_reader():
    df = pd.DataFrame({"A": np.arange(1, 100), "B": np.arange(1, 100)})
    _ = df.to_csv("./datasets/configs/dataset.csv", index=False)

    params = {
        "col_1": "A",
        "col_2": "B",
        "test_size": 0.2,
    }

    pipeline = Pipeline(
        df_path="./datasets/configs/dataset.csv",
        steps=[times_two, squared, split],
        params=params,
    )
    pipeline.process()

    assert "df" in pipeline.params.keys()
    assert "summary" in pipeline.params.keys()
    assert "stats" in pipeline.params.keys()


def test_pipeline_with_custom_reader():
    df = pd.DataFrame({"A": np.arange(1, 100), "B": np.arange(1, 100)})
    _ = df.to_csv("./datasets/configs/dataset.csv", index=False)

    params = {
        "col_1": "A",
        "col_2": "B",
        "test_size": 0.2,
        "df": "./datasets/configs/dataset.csv",
    }

    pipeline = Pipeline(
        df_path="./datasets/configs/dataset.csv",
        steps=[times_two, squared, split],
        params=params,
        custom_reader=custom_read,
    )
    pipeline.process()

    assert (
        pipeline.params["df"].loc[69, "A"]
        == pipeline.params["df_copy"].loc[69, "A"] * 2
    )
    assert (
        pipeline.params["df"].loc[42, "B"]
        == pipeline.params["df_copy"].loc[42, "B"] ** 2
    )

    assert len(pipeline.params["X_train"]) == 80


def test_add():
    df = pd.DataFrame({"A": np.arange(1, 100), "B": np.arange(1, 100)})
    _ = df.to_csv("./datasets/configs/dataset.csv", index=False)
    params = {
        "col_1": "A",
        "test_size": 0.2,
    }
    pipeline = Pipeline(
        df_path="./datasets/configs/dataset.csv",
        steps=[times_two, split],
        params=params,
    )
    pipeline.process()
    assert pipeline.params["df"].loc[42, "A"] == df.loc[42, "A"] * 2
    pipeline.add(
        squared,
        {
            "col_2": "A",
        },
        before="times_two",
    )
    pipeline.process()
    num_0 = pipeline.params["df"].loc[42, "A"]
    num_1 = df.loc[42, "A"]
    assert num_0 == (num_1 ** 2) * 2
    pipeline.remove("squared")
    pipeline.add(squared, {"col_2": "A"}, after="read_file")
    pipeline.process()
    num_0 = pipeline.params["df"].loc[42, "A"]
    num_1 = df.loc[42, "A"]
    assert num_0 == (num_1 ** 2) * 2


def test_remove():
    df = pd.DataFrame({"A": np.arange(1, 100), "B": np.arange(1, 100)})
    _ = df.to_csv("./datasets/configs/dataset.csv", index=False)
    params = {
        "col_1": "A",
        "col_2": "B",
        "test_size": 0.2,
    }
    pipeline = Pipeline(
        df_path="./datasets/configs/dataset.csv",
        steps=[times_two, squared, split],
        params=params,
    )
    pipeline.process()
    assert len(pipeline.params["X_train"]) == 80
    pipeline.remove("split")
    pipeline.process()
    assert pipeline.params["df"].shape[0] == df.shape[0]


def test_config():
    df = pd.DataFrame({"A": np.arange(1, 100), "B": np.arange(1, 100)})
    _ = df.to_csv("./datasets/configs/dataset.csv", index=False)
    params = {
        "df": "./datasets/configs/dataset.csv",
        "col_1": "A",
        "col_2": "B",
        "test_size": 0.2,
    }
    config_path = "./datasets/configs/pipeline_config.json"
    save_config(config_path, params)
    pipeline = Pipeline(
        df_path="./datasets/configs/dataset.csv",
        steps=[times_two, squared, split],
        config_file=config_path,
        custom_reader=custom_read,
    )
    pipeline.process()
    assert len(pipeline.params["X_train"]) == 80
    pipeline.remove("split")
    pipeline.process()
    assert (
        pipeline.params["df"].shape[0] == pipeline.params["df_copy"].shape[0]
    )
