@echo off  
D:\llama.cpp\bin\llama-server.exe --model D:\llama.cpp\models\google_gemma-4-26B-A4B-it-Q8_0.gguf --port 8080 --host 0.0.0.0 --ctx-size 16384 --parallel 2 --n-gpu-layers 99  
