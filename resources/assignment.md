# Module 6: Term Project Checkpoint B

[Original in Canvas](https://canvas.northwestern.edu/courses/260285/assignments/1818438?module_item_id=3948249)

## **Overview**

This checkpoint moves your term project from conceptual design to data preparation. In Checkpoint A, you defined the investment philosophy and research foundation for your proposed investment fund. Checkpoint B builds on that work by identifying the historical market data and data sources needed to evaluate your strategy.

In this assignment, you will select securities, identify reliable public data sources, and define the time period and frequency of the financial time series you will analyze. These decisions establish the empirical foundation for modeling, simulation, and performance evaluation in the remainder of the project.

**Instructions**

### Market data

Identify public sources for your data. Ensure that there are sufficient data across a number of years. Daily pricing data are sufficient, as high-frequency or intra-day trading is not required. If lucky enough to capture twenty-five years (1999–2024), the data would include the bursting of the dot-com bubble (2001–2002), the subprime mortgage financial crisis (2006–2008), the quant meltdown (July/August 2007), the European debt crisis (2009–2014), and the COVID-19 pandemic and recovery (2019–2021). Try to include at least one period of market downturn, if not a crash.

You should be able to determine total returns (dividends, interest, and capital appreciation) for each period. If the prices of securities of interest are not cyclical and your focus is long-term investments, then you might use the calendar year as the period. Many fund managers track daily prices and returns. The time-period selected for market data is critical to all of your analyses, including the Monte Carlo simulation. Note that time series databases such as TimescaleDB, which builds on PostgreSQL, can create time series aggregates, such as computing weekly or monthly prices and returns from daily prices and returns.

The Python package [yfinance](https://pypi.org/project/yfinance/) provides a convenient way to access Yahoo!'s publicly available APIs for financial time series. Check out this video from January 12, 2025: [yfinance Update 2025: What you need to know!](https://www.youtube.com/watch?v=037_883wHGo)

Another possibility for data access would be to utilize the QuantConnect platform. See Pik et al. (2025) and the Bianco (2023) interview of Jared Broad.

Measuring daily price movements for stocks, bonds, commodities, currencies, options, futures, indexes, and exchange-traded funds, we use log returns as a variable for analysis. For log daily returns, we can use this formula:

![fig-log-daily-return-white-background.png](https://canvas.northwestern.edu/courses/260285/files/25420582/preview)

This represents the daily difference in log prices, multiplied by 100 (a scaling that is convenient for daily returns). By using log units, we can more easily compare price movements across markets and securities within markets.

We often detect patterns in log returns over time. These patterns are aligned with types of trading days. For example, we may observe trading regimes or sequences of bear and bull market days, with bear market associated with negative returns and bull markets associated with positive returns.

**Advice for getting started. Make life easy for yourselves. Start with assets that have been around for at least 5 years. Start with a buy and hold strategy. Start with long positions only (no short positions). Imagine that you were Warren Buffett in 1999. You pick a group of companies based on fundamentals and hold the stocks for many years. Also assume reinvestment of all dividend distributions in the same portfolio. What does this investment (and lack of trading) strategy yield at the end of the period?**

### Methods

To justify your selection of financial securities, you can start with constrained optimization (quadratic programming perhaps), but you should add randomness to the method in some way in order to recognize market uncertainty. One way to do this would be to add randomness to the quadratic programming model by converting it into a stochastic programming model. Another way to proceed (the recommended way for this assignment) would be to employ Monte Carlo simulation.

How can you add randomness in a financial engineering problem? Instead of using a fixed set of expected returns for assets, think of returns as being defined by a distribution of possible values. That distribution could be symmetric or skewed. Some researchers in this area have suggested that expected returns should be negatively skewed to protect against catastrophic events (black swans), which are rare but have been known to engender massive market failures. By adding randomness, we acknowledge our uncertainty about markets. We do not know if prices will go up or down in the future.

You could use Monte Carlo methods for selecting securities for the fund and for making buy and sell decisions from one period to the next. Backtesting with randomly generated data makes sense as long as those data preserve time series dependencies observed in the twenty-five years of actual market data. One approach is to employ methods for generating synthetic time series data using generative adversarial networks (Yoon, Jarrett, and van der Schaar 2019).

There are many trading tools available on the World Wide Web. Check out the [TA-Lib](https://ta-lib.org/) library of technical analysis tools, written in C++ and available from Python and other languages. To get started with quantitative methods in finance and trading methods, check out this playlist of training videos by Ritvik Kharkar, which he made while a statistics graduate student at UCLA: [Stock Trading Principles](https://www.youtube.com/playlist?list=PLvcbYUQ5t0UHdm6bNx3Rnj1fdpt9sGNsm). Also, among the many sources listed under references, you will see links to training videos, papers available for download, and papers and book chapters on Course Reserves.

### Performance evaluation

To encourage people to invest in your fund, you should be able to talk about its expected performance when tested over the investment data you have collected over twenty-five years (1999–2024). What can people expect as a return on investment (ROI) after all management and brokerage fees have been deducted? Because you do not have a track record of actual investments, you will need to test your investment approach on Monte-Carlo-generated data that conform to the parameters of the twenty-five years (1999-2024) of past market data you have collected.

* **Mean reversion** is a common trading method among technical analysts. To see how to code a mean reversion method (with backtesting) in Python, check out Garner (2019), Chan 2020; Chen (2021) and the video overview from Algovibes (2022).
* **Momentum** strategies represent quantitative, rule-based approaches commonly associated with trend following. See Jegadeesh and Titman (1993), Asness et al. (2014), Antonacci (2014, 2017), D'Souza et al. (2016), Gray (2020a), and Quantopian (2025). Velissaris (2020) showed how mean reversion and momentum strategies can be combined.
* **Pairs trading** is a relative arbitrage trading strategy that involves buying (taking a long position) and selling (taking a short position) in two highly correlated securities. See Hudson and Thames (2024).

[Papers with Backtest](https://paperswithbacktest.com/) is a commercial site that provides free links to many papers showing trading approaches. Unfortunately, the site requires licensing fees for data and code.

Execute walk-forward backtesting with Monte-Carlo-generated data that have characteristics drawn from historical data. See Chapter 10 of Trivedi and Kyal (2021) for an introduction to backtesting methods with Python examples. And see López de Prado (2018) for additional discussion of backtesting methods. Imagine that you are defining your investment philosophy and trading rules in January 1999 and applying those rules for the next twenty-five years of market behavior.

Why are we using Monte Carlo methods to evaluate the investment strategy of our ETF? We are not confident that simple backtesting is sufficient, even backtesting across the past 25 years. We want to imagine hundreds or thousands of twenty-five year periods in comparable markets. We want to test across many data sets. The testing is what gives us confidence that our investment strategies (trading rules) will yield excess returns. We are data scientists. We believe that past data, when used in an intelligent way, can help us to evaluate alternative investments strategies and trading rules. Check out the videos from Gray (2023) and [Quant Radio (2024)](https://www.youtube.com/watch?v=V8OJbb_zclE).

A key measure of performance is [**alpha**](https://www.investopedia.com/terms/a/alpha.asp), which is the average returns of the fund relative to the markets. So, when reporting of the returns of your fund, be sure to report the market returns over the same period. The S&P 500 index ([SPX](https://finance.yahoo.com/quote/%5ESPX/history/)) can be used for market returns. Another key measure is [**beta**](https://www.investopedia.com/investing/beta-gauging-price-fluctuations/), which measures volatility compared with the market. The [Sharpe ratio](https://www.youtube.com/watch?v=9HD6xo2iO1g) is often used to judge performance of trading rules and asset management approaches.

When designing the performance evaluation, make sure you include fees for trading and investment management. Brokerage trading fees may vary by the companies and exchanges you work with. And your EFT will want to earn revenues in the form of management fees and possible performance-based fees, where management fees might be charged on the initial investment or annually and performance-based fees could be charged annually or on redemption/exit from the fund). The returns that EFT investors earn will be affected by fees. It may be especially instructive to allow fees to vary from zero to small percentages (say, 1 to 4 percent for management, 5 to 25 percent for performance above alpha).

An additional benefit of this assignment is the programming experience itself. Implementing trading rules and backtesting with generated time series data is challenging work. It will give you the opportunity to build on many of the things you have learned in the data science program.

Checkpoint Deliverable: Research Report (50 points)

**The deliverable for this checkpoint is a research report posted to the GitHub repository for the term project.** Answer the questions in bold type below:

* Introduction (10 points). **Why** are you conducting this research? Identify potential users of the knowledge base and application(s) that you intend to develop.
* Literature review (10 points). **Who** else has conducted research like this?
* Methods (10 points). **How** are you conducting the research? Make sure you address the issues that are the focus of this checkpoint assignment.
* Results (10 points). **What** did you learn from your research so far?
* Conclusions (10 points). **So, what** does it all mean? Do you have any concerns about the term project at this point?

| Research Report Section | At this checkpoint, your report should... |
| --- | --- |
| **Introduction** | Briefly describe the investment problem you are studying, the type of investment strategy or ETF you are developing, and why analyzing long-term market data is necessary for evaluating it. Identify potential users (investors, asset managers, researchers) and explain why your approach to portfolio construction and evaluation is useful to them. |
| **Literature Review** | Summarize prior work related to portfolio optimization, trading strategies, and quantitative investment methods. This is where you connect your project to the research and practitioner literature (e.g., Markowitz portfolio theory, Sharpe ratio, momentum or mean-reversion strategies, Monte Carlo simulation, backtesting approaches). The literature helps justify the methods you plan to use. |
| **Methods** | Describe:   * **Market data** – assets selected, data sources (e.g., Yahoo Finance, QuantConnect), time horizon, frequency (daily returns), and how returns will be calculated (e.g., log returns). * **Modeling methods** – portfolio selection approach, simulation approach (e.g., Monte Carlo), or trading rules. * **Feature engineering or variables** used in the analysis if relevant. |
| **Results** | At this stage the results will be preliminary findings, such as:   * confirmation that sufficient historical data exist. * initial observations about returns or volatility. * early insights from exploratory analysis or data preparation. |
| **Conclusions** | Reflect on what you have learned so far about the feasibility of the strategy and the adequacy of the data. Discuss any concerns, limitations, or adjustments you may need to make before implementing the modeling and simulation stages of the project. |

 Keep the end-goal in mind. By week 10 you should have defined an investment fund that is uniquely yours, that draws on research that you have conducted, and that can be implemented in an automated, algorithmic manner.

See [Structure of Formal Research Reports PDF.](https://canvas.northwestern.edu/courses/260285/files/25420488?wrap=1 "Structure-of-Formal-Research-Reports-PDF.pdf")

**References**

See [Bibliography for the Course](../../../Module%207%20_%20Volatility%20and%20Market%20Regimes/Bibliography%20for%20the%20Course.md) ([Canvas/source](https://canvas.northwestern.edu/courses/260285/pages/bibliography-for-financial-engineering)).

## Canvas assignment metadata

Module 6: Term Project Checkpoint B
Module 6: Term Project Checkpoint B
Due: Sun Nov 1, 2026 11:59pm
Due: Sun Nov 1, 2026 11:59pm
Ungraded, 50 Possible Points
50 Points Possible
Attempt
In Progress
NEXT UP: Submit Assignment
Add Comment
Unlimited Attempts Allowed
Details


- [Local Structure-of-Formal-Research-Reports-PDF.pdf](Structure-of-Formal-Research-Reports-PDF.pdf) · [Markdown](Structure-of-Formal-Research-Reports-PDF.pdf.md)
