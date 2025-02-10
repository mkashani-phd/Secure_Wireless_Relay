## Superposition
some image...

When seding a digital communication message, a tag is used by the sender and known to the receiver to verify the authenticity of the message. By superposing the message to the tag, the time and energy of just transmitting the tag is reduced.

some image...

Some parity is also sent along with the tag to verify the incorrectness and errors in the message.



## Testbed
We developed a testbed to demonstrate the experimentally calculate the error porbabilities of superposing the message and tags. We have used 2 USRP Software Defined Radios (SDRs) that are place in an office space at variable distance. This repository maintain the source code necessary to LDPC encode/decode and modulate/demodulate the data.

The repository is organized as follows
```
.
├── __pycache__/             # Compiled Python files (auto-generated, typically ignored)
├── base_matrices/           # Contains base matrices for channel coding
├── matlab_code/             # Directory for MATLAB scripts and code
├── test/                    # Contains test scripts and supporting files
│   ├── __pycache__/         # Cached files for test scripts
│   ├── base_matrices/       # Base matrices specific to tests
│   ├── channelCoding.py     # Script for channel coding operations
│   ├── config.py            # Configuration settings for testing
│   ├── rx.py                # Receiver functionality
│   └── tx.py                # Transmitter functionality
├── analyze.ipynb            # Jupyter Notebook for data analysis
├── default_config.yaml      # YAML file with default configuration settings
├── LDPC.ipynb               # Jupyter Notebook for LDPC-related operations
├── README.md                # Documentation file (you are reading this)
└── run.py                   # Main script to run the project
```


## Key Components

- **`base_matrices/`**: Contains essential base matrices for channel coding, possibly used across different scripts.
- **`matlab_code/`**: Stores MATLAB code for simulations or additional computations.
- **`test/`**: Includes test scripts and related resources:
  - `channelCoding.py`: Handles channel coding operations.
  - `config.py`: Contains configuration settings for tests.
  - `rx.py` and `tx.py`: Receiver and transmitter modules respectively.
- **`analyze.ipynb`**: A notebook for analyzing data and results.
- **`default_config.yaml`**: YAML file containing default configurations.
- **`LDPC.ipynb`**: Notebook focusing on LDPC (Low-Density Parity-Check) code operations.
- **`run.py`**: The main entry point to execute the project.

## Post Processing
When the message is received, it is recorded and stored to be processed after completion instead of real time. By using this method, more data is collected efficiently.