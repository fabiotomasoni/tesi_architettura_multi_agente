#!/bin/sh
# Componente fidato con il solo NET_ADMIN; nessun codice di agente o tool.
set -eu
iptables -P INPUT DROP
iptables -P OUTPUT DROP
iptables -P FORWARD DROP
ip6tables -P INPUT DROP
ip6tables -P OUTPUT DROP
ip6tables -P FORWARD DROP
# Docker può fare DNAT al proprio resolver: blocco DNS prima della traduzione.
iptables -t raw -A OUTPUT -p udp --dport 53 -j DROP
iptables -t raw -A OUTPUT -p tcp --dport 53 -j DROP
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
# Solo controlli locali, non resolver Docker 127.0.0.11.
iptables -A INPUT -s 127.0.0.1 -d 127.0.0.1 -j ACCEPT
iptables -A OUTPUT -s 127.0.0.1 -d 127.0.0.1 -j ACCEPT
case "$TESI_NETWORK_ROLE" in
 gateway)
  iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
  iptables -A OUTPUT -p tcp -d 172.30.241.3 --dport 8001 -j ACCEPT
  iptables -A OUTPUT -p tcp -d 172.30.242.3 --dport 8002 -j ACCEPT
  ;;
 markets)
  iptables -A INPUT -p tcp -s 172.30.241.2 --dport 8001 -j ACCEPT
  iptables -A OUTPUT -p tcp -d 172.30.241.2 --dport 8000 -j ACCEPT
  ;;
 tax)
  iptables -A INPUT -p tcp -s 172.30.242.2 --dport 8002 -j ACCEPT
  iptables -A OUTPUT -p tcp -d 172.30.242.2 --dport 8000 -j ACCEPT
  ;;
 *) exit 1;;
esac
# Non abilitare forwarding o aggiungere route verso l'host.
touch /run/netguard-ready
exec sleep infinity
