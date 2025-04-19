%undefine _auto_set_build_flags
%define _use_weak_usergroup_deps 1

%{?systemd_requires}

# SELinux Related definitions
%global selinuxtype targeted
%global moduletype  services
%global modulenames vpp-custom

# Usage: _format var format
#   Expand 'modulenames' into various formats as needed
#   Format must contain '$x' somewhere to do anything useful
%global _format() export %1=""; for x in %{modulenames}; do %1+=%2; %1+=" "; done;

# Relabel files
%global relabel_files() \ # ADD files in *.fc file

# Version of distribution SELinux policy package
%global selinux_policyver 3.13.1-128.6.fc22

Name: vpp
Summary: Vector Packet Processing
License: ASL 2.0
Version: 25.06
Release: 0.186.rc0.20250418gite22e6cbbb%{?dist}
Source: %{name}-%{version}-rc0~186_ge22e6cbbb.tar.xz
BuildRequires: vpp-ext-deps
BuildRequires: systemd chrpath
BuildRequires: python3-devel python3-ply
BuildRequires: check-devel subunit-devel
BuildRequires: selinux-policy-devel
BuildRequires: libmnl-devel libnl3-devel
BuildRequires: apr-devel numactl-devel
BuildRequires: openssl-devel libunwind-devel
BuildRequires: elfutils-libelf-devel libpcap-devel
BuildRequires: clang cmake ninja-build
%if 0%{?fedora} >= 41
BuildRequires: openssl-devel-engine
%endif
Requires: vpp-lib = %{version}-%{release}, vpp-selinux-policy = %{version}-%{release}, net-tools, pciutils

%description
This package provides VPP executables: vpp, vpp_api_test
vpp - the vector packet engine
vpp_api_test - vector packet engine API test tool

%package lib
Summary: VPP libraries
Group: System Environment/Libraries
Requires: vpp-selinux-policy = %{version}-%{release}

%description lib
This package contains the VPP shared libraries, including:
vppinfra - foundation library supporting vectors, hashes, bitmaps, pools, and string formatting.
svm - vm library
vlib - vector processing library
vlib-api - binary API library
vnet -  network stack library

%package devel
Summary: VPP header files, static libraries
Group: Development/Libraries
Requires: vpp-lib

%description devel
This package contains the header files for VPP.
Install this package if you want to write a
program for compilation and linking with vpp lib.
vlib
vlibmemory
vnet - devices, classify, dhcp, ethernet flow, gre, ip, etc.
vpp-api
vppinfra

%package plugins
Summary: Vector Packet Processing--runtime plugins
Group: System Environment/Libraries
Requires: vpp = %{version}-%{release} numactl-libs
%description plugins
This package contains VPP plugins

%package api-lua
Summary: VPP api lua bindings
Group: Development/Libraries
Requires: vpp = %{version}-%{release}, vpp-lib = %{version}-%{release}

%description api-lua
This package contains the lua bindings for the vpp api

%package api-python3
Summary: VPP api python3 bindings
Group: Development/Libraries
Requires: vpp = %{version}-%{release}, vpp-lib = %{version}-%{release}
Requires: python3-setuptools

%description api-python3
This package contains the python3 bindings for the vpp api

%package selinux-policy
Summary: VPP Security-Enhanced Linux (SELinux) policy
Group: System Environment/Base
Requires(post): selinux-policy-base >= %{selinux_policyver}, selinux-policy-targeted >= %{selinux_policyver}, policycoreutils, libselinux-utils
Requires(post): python3-policycoreutils

%description selinux-policy
This package contains a tailored VPP SELinux policy

%prep
%setup -q -n %{name}-%{version}

%pre
# Add the vpp group
groupadd -f -r vpp

%build
%if 0%{?rhel} >= 10
export VPP_EXCLUDED_PLUGINS=tlsopenssl
%endif

make -C build-root V=1 PLATFORM=vpp TAG=vpp install-packages
cd extras/selinux && make -f %{_datadir}/selinux/devel/Makefile

%install
mkdir -p -m755 %{buildroot}/usr
cp -pr build-root/install-vpp-native/vpp/{bin,lib,lib64,include,share} %{buildroot}/usr/
cp -pr build-root/install-vpp-native/vpp/etc %{buildroot}

# remove RPATH from ELF binaries
src/scripts/remove-rpath %{buildroot}

mkdir -p -m755 %{buildroot}%{_unitdir}
install -p -m 644 extras/rpm/vpp.service %{buildroot}%{_unitdir}

# vppctl sockfile directory
mkdir -p -m755 %{buildroot}%{_rundir}/vpp
# vpp.log directory
mkdir -p -m755 %{buildroot}%{_localstatedir}/log/vpp

# SELinux Policy
# Install SELinux interfaces
%_format INTERFACES extras/selinux/$x.if
install -d %{buildroot}%{_datadir}/selinux/devel/include/%{moduletype}
install -p -m 644 $INTERFACES %{buildroot}%{_datadir}/selinux/devel/include/%{moduletype}
# Install policy modules
%_format MODULES extras/selinux/$x.pp
install -d %{buildroot}%{_datadir}/selinux/packages
install -m 0644 $MODULES %{buildroot}%{_datadir}/selinux/packages

# sample plugin
mkdir -p -m755 %{buildroot}%{_datadir}/doc/vpp/examples/sample-plugin/sample
cp -p src/examples/sample-plugin/sample/{*c,*h,*api} %{buildroot}%{_datadir}/doc/vpp/examples/sample-plugin/sample
# Lua bindings
cp -pr src/vpp-api/lua %{buildroot}%{_datadir}/doc/vpp/examples

%post
if [ $1 -eq 1 ] ; then
    sysctl --system
fi
%systemd_post vpp.service

%preun
%systemd_preun vpp.service

%post selinux-policy
%_format MODULES %{_datadir}/selinux/packages/$x.pp
if %{_sbindir}/selinuxenabled ; then
    %{_sbindir}/semodule -n -X 400 -s %{selinuxtype} -i $MODULES
    %{_sbindir}/load_policy
    %relabel_files
fi


%postun
%systemd_postun vpp.service
if [ $1 -eq 0 ] ; then
    echo "Uninstalling, unbind user-mode PCI drivers"
    # Unbind user-mode PCI drivers
    removed=
    pci_dirs=`find /sys/bus/pci/drivers -type d -name igb_uio -o -name uio_pci_generic -o -name vfio-pci`
    for d in $pci_dirs; do
        for f in ${d}/*; do
            [ -e "${f}/config" ] || continue
            echo ${f##*/} > ${d}/unbind
            basename `dirname ${f}` | xargs echo -n "Removing driver"; echo " for PCI ID" `basename ${f}`
            removed=y
        done
    done
    if [ -n "${removed}" ]; then
        echo "There are changes in PCI drivers, rescaning"
        echo 1 > /sys/bus/pci/rescan
    else
        echo "There weren't PCI devices binded"
    fi
else
    echo "Upgrading package, dont' unbind interfaces"
fi

%postun selinux-policy
if [ $1 -eq 0 ]; then
    %{_sbindir}/semodule -n -r %{modulenames}
    if %{_sbindir}/selinuxenabled ; then
        %{_sbindir}/load_policy
        %relabel_files
    fi
fi

%files
%doc LICENSE MAINTAINERS README.md
%defattr(-,bin,bin)
%{_unitdir}/vpp.service
%{_bindir}/vat2
%{_bindir}/vcl_test_*
%{_bindir}/vpp
%{_bindir}/vppctl
%{_bindir}/vpp_*
%{_bindir}/svm*
%dir %{_sysconfdir}/vpp
%config(noreplace) %{_sysconfdir}/sysctl.d/80-vpp.conf
%config(noreplace) %{_sysconfdir}/vpp/startup.conf

%defattr(-,root,vpp)
%{_rundir}/vpp

%defattr(-,root,root)
%{_localstatedir}/log/vpp

%files lib
%defattr(-,bin,bin)
%{_libdir}/lib*.so.*
%{_libdir}/libvcl_ldpreload.so
%{_libdir}/libvppmem_preload.so
%dir %{_datadir}/vpp
%dir %{_datadir}/vpp/api
%{_datadir}/vpp/api/core

%files api-lua
%defattr(644,root,root,755)
%dir %{_datadir}/doc/vpp/examples
%{_datadir}/doc/vpp/examples/lua

%files api-python3
%defattr(644,root,root,755)
%{python3_sitelib}/vpp_*

%files selinux-policy
%doc extras/selinux/selinux_doc.rst
%defattr(-,root,root,0755)
%attr(0644,root,root) %{_datadir}/selinux/packages/*.pp
%attr(0644,root,root) %{_datadir}/selinux/devel/include/%{moduletype}/*.if

%files devel
%defattr(-,bin,bin)
%{_bindir}/vppapigen
%{_bindir}/vapi_*.py
%{_libdir}/cmake/vpp
%{_libdir}/lib*.so
%exclude %{_libdir}/libvcl_ldpreload.so
%exclude %{_libdir}/libvppmem_preload.so
%{_datadir}/vpp/*.py
%defattr(644,root,root,755)
%dir %{_datadir}/doc/vpp
%dir %{_datadir}/doc/vpp/examples
%{_datadir}/doc/vpp/examples/sample-plugin
%{_includedir}/*

%files plugins
%defattr(-,bin,bin)
%{_libdir}/vpp_plugins
%{_libdir}/vpp_api_test_plugins
%{_libdir}/vpp_crypto_engines
%{_libdir}/vat2_plugins
%{_datadir}/vpp/api/plugins
