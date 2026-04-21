"""Основная логика TCP пинга."""

import socket
import struct
import sys
import time
import random
from typing import List, Optional, Callable

from tcping.models import PingResult

try:
    from tcping.output import DEBUG_MODE
except ImportError:
    DEBUG_MODE = False


class TCPinger:
    """Класс для выполнения TCP пингов."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self.is_windows = sys.platform == 'win32'

    def _calculate_checksum(self, data: bytes) -> int:
        """Рассчёт контрольной суммы для TCP-пакета."""
        s = 0
        for i in range(0, len(data), 2):
            w = (data[i] << 8) + (data[i + 1] if i + 1 < len(data) else 0)
            s += w
        s = (s >> 16) + (s & 0xFFFF)
        s = ~s & 0xFFFF
        return s

    def _resolve_host(self, host: str) -> List[tuple]:
        """Разрешает имя хоста в список."""
        try:
            addrinfo = socket.getaddrinfo(
                host, None, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
            result = []
            seen = set()
            for addr in addrinfo:
                ip = addr[4][0]
                family = addr[0]
                if ip not in seen:
                    seen.add(ip)
                    result.append((ip, family))
            if DEBUG_MODE:
                ips = [ip for ip, _ in result]
                print(f"[DEBUG] Resolved {host} to: {', '.join(ips)}", file=sys.stderr)
            return result
        except socket.gaierror as e:
            if DEBUG_MODE:
                print(f"[DEBUG] DNS resolution failed for {host}: {e}", file=sys.stderr)
            return []

    def _send_syn_windows(self, ip: str, port: int) -> bool:
        """Отправляет SYN-пакет на Windows используя обычный сокет."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect_ex((ip, port))
            sock.close()
            if DEBUG_MODE:
                print(f"[DEBUG] Windows knock sent to {ip}:{port}", file=sys.stderr)
            return True
        except Exception as e:
            if DEBUG_MODE:
                print(f"[DEBUG] Windows knock failed to {ip}:{port}: {e}", file=sys.stderr)
            return False

    def _send_syn(self, ip: str, port: int, family: int) -> bool:
        """Отправляет один SYN-пакет на указанный порт."""
        if self.is_windows:
            return self._send_syn_windows(ip, port)

        try:
            if family == socket.AF_INET:
                sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            else:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_TCP)
                try:
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_HDRINCL, 1)
                except AttributeError:
                    pass
        except PermissionError:
            if DEBUG_MODE:
                print("[DEBUG] Raw socket requires root/admin", file=sys.stderr)
            return False

        src_port = random.randint(10000, 65000)
        seq = random.randint(0, 2 ** 31 - 1)

        tcp_header = struct.pack(
            '!HHLLBBHHH',
            src_port, port, seq, 0,
            (5 << 4), 0x02, 8192, 0, 0
        )

        if family == socket.AF_INET:
            pseudo_header = struct.pack(
                '!4s4sBBH',
                socket.inet_aton('0.0.0.0'),
                socket.inet_aton(ip),
                0, socket.IPPROTO_TCP, len(tcp_header)
            )
            checksum = self._calculate_checksum(pseudo_header + tcp_header)
            tcp_header = struct.pack(
                '!HHLLBBHHH',
                src_port, port, seq, 0,
                (5 << 4), 0x02, 8192, checksum, 0
            )
            sock.sendto(tcp_header, (ip, 0))
        else:
            ipv6_addr = socket.inet_pton(socket.AF_INET6, ip)
            pseudo_header = struct.pack(
                '!16s16sBBH',
                ipv6_addr, ipv6_addr, 0, socket.IPPROTO_TCP, len(tcp_header)
            )
            checksum = self._calculate_checksum(pseudo_header + tcp_header)
            tcp_header = struct.pack(
                '!HHLLBBHHH',
                src_port, port, seq, 0,
                (5 << 4), 0x02, 8192, checksum, 0
            )
            sock.sendto(tcp_header, (ip, 0, 0, 0))

        sock.close()
        return True

    def knock(self, host: str, ports: List[int], delay: float = 0.1) -> bool:
        """Отправляет SYN-пакеты на указанные порты в заданном порядке."""
        if DEBUG_MODE:
            print(f"[DEBUG] Starting port knocking sequence: {ports}", file=sys.stderr)

        ips = self._resolve_host(host)
        if not ips:
            if DEBUG_MODE:
                print(f"[DEBUG] Cannot resolve host for knocking: {host}", file=sys.stderr)
            return False

        ip, family = ips[0]

        for port in ports:
            if DEBUG_MODE:
                print(f"[DEBUG] Knocking on {ip}:{port}", file=sys.stderr)
            self._send_syn(ip, port, family)
            time.sleep(delay)

        if DEBUG_MODE:
            print(f"[DEBUG] Port knocking completed", file=sys.stderr)
        return True

    def _syn_scan_ipv4(self, ip: str, port: int) -> tuple:
        """IPv4 SYN scan через raw socket."""
        if self.is_windows:
            return self._connect_scan_ipv4(ip, port)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        except PermissionError:
            if DEBUG_MODE:
                print("[DEBUG] IPv4 raw socket requires root/admin", file=sys.stderr)
            return (False, None, "permission denied (need sudo)")

        src_port = random.randint(10000, 65000)
        seq = random.randint(0, 2 ** 31 - 1)

        tcp_header = struct.pack(
            '!HHLLBBHHH',
            src_port, port, seq, 0,
            (5 << 4), 0x02, 8192, 0, 0
        )

        pseudo_header = struct.pack(
            '!4s4sBBH',
            socket.inet_aton('0.0.0.0'),
            socket.inet_aton(ip),
            0, socket.IPPROTO_TCP, len(tcp_header)
        )
        checksum = self._calculate_checksum(pseudo_header + tcp_header)

        tcp_header = struct.pack(
            '!HHLLBBHHH',
            src_port, port, seq, 0,
            (5 << 4), 0x02, 8192, checksum, 0
        )

        sock.sendto(tcp_header, (ip, 0))

        start = time.perf_counter()
        sock.settimeout(self.timeout)

        try:
            while True:
                data, _ = sock.recvfrom(4096)
                elapsed = time.perf_counter() - start
                ip_header = data[0:20]
                iph_len = (ip_header[0] & 0x0F) * 4
                tcp_segment = data[iph_len:iph_len + 20]
                flags = tcp_segment[13]
                if flags & 0x12 == 0x12:
                    sock.close()
                    return (True, elapsed, None)
        except socket.timeout:
            sock.close()
            return (False, None, f"timeout after {self.timeout}s")
        except Exception as e:
            sock.close()
            return (False, None, f"error: {e}")

    def _connect_scan_ipv4(self, ip: str, port: int) -> tuple:
        """Обычный connect scan для Windows."""
        start = time.perf_counter()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((ip, port))
            elapsed = time.perf_counter() - start
            sock.close()
            return (True, elapsed, None)
        except socket.timeout:
            return (False, None, f"timeout after {self.timeout}s")
        except ConnectionRefusedError:
            return (False, None, "connection refused")
        except Exception as e:
            return (False, None, f"error: {e}")

    def _syn_scan_ipv6(self, ip: str, port: int) -> tuple:
        """IPv6 SYN scan через raw socket."""
        if self.is_windows:
            return self._connect_scan_ipv6(ip, port)

        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_TCP)
            try:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_HDRINCL, 1)
            except AttributeError:
                pass
        except (PermissionError, OSError):
            if DEBUG_MODE:
                print(f"[DEBUG] IPv6 raw socket not available, using connect+RST", file=sys.stderr)
            return self._connect_scan_ipv6(ip, port)

        src_port = random.randint(10000, 65000)
        seq = random.randint(0, 2 ** 31 - 1)

        tcp_header = struct.pack(
            '!HHLLBBHHH',
            src_port, port, seq, 0,
            (5 << 4), 0x02, 8192, 0, 0
        )

        ipv6_addr = socket.inet_pton(socket.AF_INET6, ip)
        pseudo_header = struct.pack(
            '!16s16sBBH',
            ipv6_addr, ipv6_addr, 0, socket.IPPROTO_TCP, len(tcp_header)
        )
        checksum = self._calculate_checksum(pseudo_header + tcp_header)

        tcp_header = struct.pack(
            '!HHLLBBHHH',
            src_port, port, seq, 0,
            (5 << 4), 0x02, 8192, checksum, 0
        )

        sock.sendto(tcp_header, (ip, 0, 0, 0))

        start = time.perf_counter()
        sock.settimeout(self.timeout)

        try:
            while True:
                data, _ = sock.recvfrom(4096)
                elapsed = time.perf_counter() - start
                if len(data) > 40:
                    tcp_start = 40
                    flags = data[tcp_start + 13]
                    if flags & 0x12 == 0x12:
                        sock.close()
                        return (True, elapsed, None)
        except socket.timeout:
            sock.close()
            return (False, None, f"timeout after {self.timeout}s")
        except Exception as e:
            sock.close()
            return (False, None, f"error: {e}")

    def _connect_scan_ipv6(self, ip: str, port: int) -> tuple:
        """Обычный connect scan для IPv6 на Windows."""
        start = time.perf_counter()
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((ip, port))
            elapsed = time.perf_counter() - start
            sock.close()
            return (True, elapsed, None)
        except socket.timeout:
            return (False, None, f"timeout after {self.timeout}s")
        except ConnectionRefusedError:
            return (False, None, "connection refused")
        except Exception as e:
            return (False, None, f"error: {e}")

    def ping_once(self, host: str, port: int, knock_ports: Optional[List[int]] = None) -> PingResult:
        """Выполняет одну попытку."""
        if DEBUG_MODE:
            print(f"[DEBUG] Starting scan to {host}:{port}", file=sys.stderr)

        if knock_ports:
            if DEBUG_MODE:
                print(f"[DEBUG] Port knocking sequence: {knock_ports}", file=sys.stderr)
            self.knock(host, knock_ports)

        ips = self._resolve_host(host)
        if not ips:
            return PingResult(
                success=False,
                host=host,
                port=port,
                duration=None,
                error_message=f"DNS resolution failed: {host}",
            )

        last_error = None

        for ip, family in ips:
            if DEBUG_MODE:
                print(f"[DEBUG] Trying {ip} (family={family})...", file=sys.stderr)

            if family == socket.AF_INET:
                success, elapsed, error = self._syn_scan_ipv4(ip, port)
            else:
                success, elapsed, error = self._syn_scan_ipv6(ip, port)

            if success:
                if DEBUG_MODE:
                    print(f"[DEBUG] Connected to {ip} in {elapsed * 1000:.2f}ms", file=sys.stderr)
                return PingResult(
                    success=True,
                    host=host,
                    port=port,
                    duration=elapsed,
                    error_message=None,
                )
            else:
                last_error = error
                if DEBUG_MODE:
                    print(f"[DEBUG] Failed {ip}: {error}", file=sys.stderr)
                continue

        return PingResult(
            success=False,
            host=host,
            port=port,
            duration=None,
            error_message=last_error or "connection failed",
        )

    def ping_many(
            self,
            host: str,
            port: int,
            count: int,
            interval: float = 1.0,
            knock_ports: Optional[List[int]] = None,
            stream_callback: Optional[Callable[[PingResult], None]] = None,
    ) -> List[PingResult]:
        """Выполняет серию соединений с интервалом."""
        if DEBUG_MODE:
            print(f"[DEBUG] Starting ping_many: {host}:{port}, count={count}, interval={interval}",
                  file=sys.stderr)

        results = []
        for i in range(count):
            result = self.ping_once(host, port, knock_ports=knock_ports)
            results.append(result)

            if stream_callback:
                stream_callback(result)

            if i < count - 1:
                time.sleep(interval)

        if DEBUG_MODE:
            print(f"[DEBUG] ping_many completed", file=sys.stderr)

        return results

    def ping_hosts_from_file(
            self, hosts_file_path: str, count: int, interval: float
    ) -> dict:
        """Выполняет пинг для списка хостов из файла."""
        from tcping.cli import parse_hosts_file
        from tcping.models import Stats

        if DEBUG_MODE:
            print(f"[DEBUG] Reading hosts from file: {hosts_file_path}", file=sys.stderr)

        targets = parse_hosts_file(hosts_file_path)
        results_dict = {}

        for host, port in targets:
            if DEBUG_MODE:
                print(f"[DEBUG] Processing target: {host}:{port}", file=sys.stderr)

            ping_results = self.ping_many(host, port, count, interval)
            stats = Stats.from_results(host, port, ping_results)
            results_dict[(host, port)] = stats

        return results_dict
