# stockvalue-exporter

[Link to README in Japanese (README.ja.md)](./README.ja.md)

stockvalue-exporter is a custom exporter for Prometheus, designed to fetch stock price information.

## Key Features

- Integrates with Prometheus to monitor stock price information.
- Easily deployable and runnable using Docker.
- Utilizes the yfinance library to fetch stock price information.

## Technology Stack

This project primarily uses Python and Docker.
The yfinance library is used to fetch stock price information.

## Installation

You can easily get started by pulling the Docker image.

```
docker pull mizucopo/stockvalue-exporter:latest
```

## How to Use

Launch the stockvalue-exporter Docker container using the following command.

```
docker run -v config.json:/app/config.json -p 9100:9100 mizucopo/stockvalue-exporter:latest
```

## How to Contribute

If you are interested in contributing to this project, please send a pull request or open an issue to start a discussion.

## License

This project is published under the MIT License. For more details, please refer to the [LICENSE file](/LICENSE).

## Documentation

This README file serves as the project's documentation.

## Contact

If you have any questions or need support, please feel free to contact X ([@mizu_copo](https://twitter.com/mizu_copo)).
