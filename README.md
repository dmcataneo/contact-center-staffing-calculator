# Contact center staffing and cost calculator

A Streamlit app that estimates the team and the cost of running a single
service queue, from the contact volume per time interval, the average
handle time and a service-level target. It compares three scenarios:
hiring more people, cutting handle time (productivity), or assuming an
automation removes part of the contacts from the queue (a hypothesis).

Built to support operational decisions with the math visible. It is not
a guaranteed forecast. See "Assumptions and limits" below.

## Running it

You need Python 3.10 or newer installed
(<https://www.python.org/downloads/>). On Windows, check the
"Add python.exe to PATH" option during installation.

### Windows

```bat
cd path\to\project
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### Mac / Linux

```bash
cd path/to/project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The browser opens automatically at `http://localhost:8501`.

## Using it

1. Upload a CSV with two columns: `period` (e.g. `08:00`) and `contacts`
   (expected volume in that interval). Without a CSV, the app uses the
   sample data in `data/sample_demand.csv` - that data is fictional.
2. Adjust in the sidebar: hourly cost per agent, average handle time
   (AHT), service-level target and target wait time.
3. Compare the scenarios: base, productivity (lower AHT) and automation
   (lower volume - a hypothesis to test, not proven savings).

Reading the charts: the "theoretical maximum capacity" line shows how
many contacts the staffed team would handle at 100% occupancy. Because
the team is sized to hit the service-level target (not to run at the
limit), expected real-world occupancy stays below 100%, which is why
the line sits above the demand bars.

## Tests

```bash
pytest
```

The tests cover the math model (Erlang B/C, service level, average speed
of answer, staffing, capacity and cost) against hand-calculated
reference values and a second, independent log-space implementation.

## Structure

```
app.py                  Streamlit interface (charts and scenarios)
src/model.py            math: Erlang C, service level, costs
data/sample_demand.csv  fictional sample data
tests/test_model.py     automated model tests
```

## Assumptions and limits

The results hold under these assumptions (Erlang C model):

- Single queue, with identical agents 100% dedicated to it.
- Random (Poisson) arrivals and exponentially distributed handle times.
- No abandonment: every contact waits until it is answered.
- No breaks, absences or training (shrinkage). In practice the real team
  needs to be larger than the calculated one; the adjustment varies by
  operation. Add it on top of the model result for your own reality.
- No multiple channels and no priorities between contacts.
- The automation scenario is a hypothesis about volume, used to measure
  sensitivity - it is not measured savings.

Use it to compare scenarios and support decisions. Validate against real
operational data before hiring or letting people go.
