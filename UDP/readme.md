# How to run
Note: use `python3` command instead of `python` if on Mac.
Note: Start the server again after each client request to do the handshake again

Todo: Increase Packet Size?
Todo: Test for multiple clients

Assumption: 
    - Selective repeat is implemented for only one packet of 1024 byte will be sent
    - Client will close after sending the last ACK, If that ACK is dropped, then the server will keep sending packets while the client is closed

1. Run the Router: 
    - Relibale: `cd Router && router_x64.exe --port=3000 --drop-rate=0.0 --max-delay=0ms --seed=1`
    - Delay: `cd Router && router_x64.exe --port=3000 --drop-rate=0.0 --max-delay=4000ms --seed=1`
    - Drop Rate: `cd Router && router_x64.exe --port=3000 --drop-rate=0.5 --max-delay=0ms --seed=1`
    - Both: `cd Router && router_x64.exe --port=3000 --drop-rate=0.5 --max-delay=2000ms --seed=1`
    - Note: We are using a delay of 5s as server and client times out at 3s

2. Run the server: `cd Server && python httpfs.py -p 8080 -v`
    - Here, you can also specifcy the directory path to read/write files in with `-d` (default: /Data)
    - You can also specify port with `-p` (default: 8080)

3. Run the client: 
    - Read from directory `cd Client && python httpc.py GET http://localhost:8080`
    - Read from specific file in directory `cd Client && python httpc.py GET http://localhost:8080/text.txt`
    - Write to a specific file in directory `cd Client && python httpc.py POST http://localhost:8080/text.txt -d "hello TAA!"`
    - Test cannot read outside of default directory: `cd Client && python httpc.py GET http://localhost:8080/../cannot-access.txt`
    - Test content type and content disposition: `cd Client && python httpc.py GET http://localhost:8080/hello.json -v`
    - Test multiple connections
        - Uncomment the time.sleep(10) line in HTTPServerLibrary.py
        - Spin up 2 new terminal instances and type:
            - `cd Client && python httpc.py GET http://localhost:8080`
            - `cd Client && python httpc.py POST http://localhost:8080/text.txt -d "hello TAA - 1!"`
            - `cd Client && python httpc.py POST http://localhost:8080/text.txt -d "hello TAA - 2!"`