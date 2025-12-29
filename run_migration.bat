@echo off
chcp 65001 > nul
echo sim| python migrate_encrypt_passwords.py
