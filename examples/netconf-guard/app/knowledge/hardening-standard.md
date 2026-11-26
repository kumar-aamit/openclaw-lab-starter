# Network hardening standard v2

Applies to every switch, router and firewall. Each rule has a number that reviews cite.

## 1 Management access

- **1.1 SSH version 2 only.** Version 1 has practical attacks. Use `ip ssh version 2` or `ssh version 2`.
- **1.2 No Telnet.** VTY lines accept SSH only: `transport input ssh`. Telnet sends passwords in clear text.
- **1.3 Management from the management network only.** Apply an access-class to VTY lines and restrict
  firewall SSH to the inside management subnet. Never allow management from the internet.
- **1.4 No plain HTTP management.** `no ip http server`. Use HTTPS only where a GUI is required.
- **1.5 Idle sessions time out.** `exec-timeout 10 0` on console and VTY lines.

## 2 AAA and passwords

- **2.1 Enable secret, not enable password.** Use `enable secret` with type 8 or 9. Type 7 and clear-text
  enable passwords are reversible and are not allowed.
- **2.2 Local users use secret.** `username <name> secret <value>`, never `password 0` or `password 7`.
- **2.3 Password encryption on.** `service password-encryption` as a backstop for any remaining type 7 values.
- **2.4 Central AAA.** `aaa new-model` with TACACS+ for login and command authorization; local users are
  for break-glass access only.
- **2.5 Login protection.** `login block-for 120 attempts 5 within 60` to slow guessing.

## 3 SNMP, logging and time

- **3.1 No default SNMP communities.** Remove `public` and `private`. Use SNMPv3 with auth and priv.
  Write access over SNMP is never allowed.
- **3.2 SNMP limited by ACL.** Only the monitoring servers may poll.
- **3.3 Remote logging.** Send logs to the syslog servers with `logging host`; keep a local buffer too.
- **3.4 Authenticated NTP.** `ntp authenticate` with a trusted key, so time cannot be spoofed.
- **3.5 Timestamps on logs.** `service timestamps log datetime msec localtime show-timezone`.

## 4 Switching

- **4.1 BPDU Guard with PortFast.** Every access port with `spanning-tree portfast` also has
  `spanning-tree bpduguard enable`.
- **4.2 No users in VLAN 1.** Put access ports in a named user VLAN; VLAN 1 carries no user traffic.
- **4.3 Unused ports shut.** `shutdown` and move to the parking VLAN 999.
- **4.4 DHCP snooping on user VLANs.** Trust only the uplinks.
- **4.5 Storm control on access ports.** `storm-control broadcast level 5`.

## 5 Firewall policy

- **5.1 No any-to-any rules on the outside.** Inbound rules permit named services to named hosts and end
  with `deny ip any any log`.
- **5.2 Management from inside only.** SSH, HTTPS and ASDM only from the inside management subnet.
- **5.3 Restrict ICMP on the outside.** Permit echo-reply and unreachable only.
- **5.4 Strong TLS.** `ssl cipher tlsv1.2 high`; no low or medium ciphers.
- **5.5 Threat detection on.** `threat-detection basic-threat` and statistics for access lists.
