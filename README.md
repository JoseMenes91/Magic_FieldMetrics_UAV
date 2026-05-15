# Magic_FieldMetrics_UAV
QGIS plugin for agricultural microplot trials. Extracts spatial statistics, coverage (%), volume metrics, and global stats (Z-Score, CV) for each vector polygon across every band of a UAV orthomosaic.
<img width="96" height="96" alt="image" src="https://github.com/user-attachments/assets/40272b9c-6b09-4527-848d-bbbb1446faf6" />



## 🛠 Installation

1. Download or clone this repository.
2. Copy the `microplot_generator` folder into your local QGIS plugins directory: (e.g., `C:\Users\YourUser\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins`).

 <img width="651" height="341" alt="image" src="https://github.com/user-attachments/assets/06502863-1624-48f6-96f2-2e421811ab03" />
<img width="988" height="750" alt="image" src="https://github.com/user-attachments/assets/c715fc19-04e3-4601-afab-f05e53ac147a" />
<img width="839" height="262" alt="image" src="https://github.com/user-attachments/assets/69b1add6-b18a-4a74-9391-36b2198fe5ab" />




## 📖 Quick Start Guide
Layer selection: Upon opening the tool, simply select your Raster layer (orthomosaic or height model) and your Vector layer (your microplot polygons).
Metrics selection: You can choose as many statistics and percentiles as you want. The plugin will automatically calculate the values for each polygon and across every raster band.
⚠️ Special Considerations
Some metrics require specific raster preparations:

Vegetal Coverage (%): The input raster layer must have the soil masked (bare soil pixels must be set to NoData). The plugin will calculate the proportion of valid (plant) pixels relative to the total polygon area.
Volume Metrics: The input raster must necessarily be a Canopy Height Model (CHM), where the ground level equals 0.
Canopy Volume ($m^3$): Sums all positive heights and multiplies them by the pixel area ($GSD^2$).
Volume Index: This is the Canopy Volume divided by the total surface area of the microplot.
🌍 Global Trial Metrics
The Z-Score and Robust Scaler are statistics primarily designed to work with the thermal band.

Unlike the rest of the metrics, the algorithm does not evaluate a plot in isolation; it first internally collects the pixels from all vector polygons (all microplots) to build the real distribution of the entire trial. Once it establishes the population behavior, it standardizes each plot:

Z-Score: Indicates how many standard deviations a plot is above or below the overall trial average.
Formula: (Plot Mean - Global Trial Mean) / Global Standard Deviation
Robust Scaler: Fulfills the same function as the Z-Score, but is highly resistant to extreme values (such as hot edges or anomalies).
Formula: (Plot Mean - Global Trial Median) / Global Interquartile Range
