#!/usr/bin/env python3

import re
from ansible.errors import AnsibleFilterError

class FilterModule(object):
    def filters(self):
        return {
            'extract_config_sections': self.extract_config_sections,
            'normalize_config': self.normalize_config,
            'compare_with_baseline': self.compare_with_baseline
        }

    def extract_config_sections(self, running_config, network_os):
        """Extract relevant configuration sections based on baseline patterns"""
        
        if network_os in ['ios', 'nxos', 'eos']:
            return self._extract_cisco_sections(running_config)
        elif network_os == 'comware':
            return self._extract_h3c_sections(running_config)
        elif network_os == 'ce':
            return self._extract_huawei_sections(running_config)
        else:
            # Return full config if we don't have specific extraction logic
            return running_config

    def _extract_cisco_sections(self, config):
        """Extract Cisco IOS relevant sections"""
        if not config:
            return ""
            
        patterns = [
            r'service password-encryption.*',
            r'banner login.*?(?=\n[a-z]|\n!|\Z)',
            r'line con 0.*?(?=\nline|\n[a-z]|\Z)',
            r'line vty.*?(?=\nline|\n[a-z]|\Z)',
            r'snmp-server community.*',
            r'tacacs-server host.*'
        ]
        
        extracted = []
        for pattern in patterns:
            matches = re.findall(pattern, config, re.MULTILINE | re.DOTALL)
            if matches:
                extracted.extend(matches)
        
        return '\n'.join(extracted)

    def _extract_h3c_sections(self, config):
        """Extract H3C Comware relevant sections"""
        if not config:
            return ""
            
        patterns = [
            r'header login.*?(?=\n[a-z]|\n#|\Z)',
            r'line aux.*?(?=\nline|\n[a-z]|\Z)',
            r'line vty.*?(?=\nline|\n[a-z]|\Z)',
            r'hwtacacs scheme.*',
            r'snmp-agent community.*'
        ]
        
        extracted = []
        for pattern in patterns:
            matches = re.findall(pattern, config, re.MULTILINE | re.DOTALL)
            if matches:
                extracted.extend(matches)
        
        return '\n'.join(extracted)

    def _extract_huawei_sections(self, config):
        """Extract Huawei CE relevant sections"""
        if not config:
            return ""
            
        patterns = [
            r'user-interface console.*?(?=\nuser-interface|\n[a-z]|\Z)',
            r'user-interface vty.*?(?=\nuser-interface|\n[a-z]|\Z)',
            r'hwtacacs-server.*',
            r'snmp-agent community.*'
        ]
        
        extracted = []
        for pattern in patterns:
            matches = re.findall(pattern, config, re.MULTILINE | re.DOTALL)
            if matches:
                extracted.extend(matches)
        
        return '\n'.join(extracted)

    def normalize_config(self, config, network_os):
        """Normalize configuration for comparison"""
        if not config:
            return []
        
        # Remove comments and empty lines
        lines = []
        for line in config.split('\n'):
            line = line.strip()
            if line and not line.startswith('!') and not line.startswith('#'):
                lines.append(line)
        
        return lines

    def compare_with_baseline(self, running_config_lines, baseline_lines, network_os):
        """Compare running config with baseline and return detailed analysis"""
        
        if not running_config_lines:
            running_config_lines = []
        if not baseline_lines:
            baseline_lines = []
            
        missing_configs = []
        different_configs = []
        
        # Check for missing baseline configurations
        for baseline_line in baseline_lines:
            if baseline_line not in running_config_lines:
                # Check if it's a partial match (for incomplete configurations)
                partial_match = False
                for running_line in running_config_lines:
                    if self._is_similar_config(baseline_line, running_line, network_os):
                        partial_match = True
                        if baseline_line != running_line:
                            different_configs.append({
                                'baseline': baseline_line,
                                'running': running_line
                            })
                        break
                
                if not partial_match:
                    missing_configs.append(baseline_line)
        
        has_differences = bool(missing_configs or different_configs)
        
        return {
            'has_differences': has_differences,
            'missing_configs': missing_configs,
            'extra_configs': [],  # Not checking for extra configs for now
            'different_configs': different_configs,
            'summary': self._generate_summary(missing_configs, [], different_configs)
        }

    def _is_similar_config(self, baseline_line, running_line, network_os):
        """Check if two configuration lines are similar (same command family)"""
        
        # Simple comparison for now - check if first word matches
        try:
            baseline_first = baseline_line.split()[0] if baseline_line.split() else ""
            running_first = running_line.split()[0] if running_line.split() else ""
            return baseline_first == running_first
        except:
            return False

    def _generate_summary(self, missing, extra, different):
        """Generate a human-readable summary of differences"""
        summary_parts = []
        
        if missing:
            summary_parts.append(f"Missing {len(missing)} baseline configuration(s)")
        
        if different:
            summary_parts.append(f"Found {len(different)} configuration difference(s)")
        
        if not summary_parts:
            return "Configuration matches baseline"
        
        return "; ".join(summary_parts)