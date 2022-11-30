%undefine _auto_set_build_flags
%define _mu_build_dir    %{_builddir}/%{name}-%{version}/build-root
%define _vpp_install_dir install-vpp-native

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
Version: 23.02
Release: 0.146.rc0.20221130git5010bbd3c%{?dist}
Source: %{name}-%{version}-rc0~146_g5010bbd3c.tar.xz
BuildRequires: vpp-ext-deps
BuildRequires: systemd-rpm-macros chrpath
BuildRequires: openssl openssl-devel
BuildRequires: python3-devel python3-ply
BuildRequires: check-devel selinux-policy-devel
BuildRequires: libmnl-devel libnl3-devel
BuildRequires: libffi-devel apr-devel numactl-devel
BuildRequires: elfutils-libelf-devel libuuid-devel
BuildRequires: clang cmake ninja-build
Requires: vpp-lib = %{version}-%{release}, vpp-selinux-policy = %{version}-%{release}, net-tools, pciutils
Requires: libffi-devel

%description
This package provides VPP executables: vpp, vpp_api_test, vpp_json_test
vpp - the vector packet engine
vpp_api_test - vector packet engine API test tool
vpp_json_test - vector packet engine JSON test tool

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
Requires: vpp = %{version}-%{release}, vpp-lib = %{version}-%{release}, libffi-devel
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
make -C build-root PLATFORM=vpp TAG=vpp install-packages
cd %{_mu_build_dir}/../src/vpp-api/python && %py3_build
cd %{_mu_build_dir}/../extras/selinux && make -f %{_datadir}/selinux/devel/Makefile

%install
#
# binaries
#
mkdir -p -m755 %{buildroot}%{_bindir}
mkdir -p -m755 %{buildroot}%{_unitdir}
install -p -m 755 %{_mu_build_dir}/%{_vpp_install_dir}/vpp/bin/* %{buildroot}%{_bindir}

# api
mkdir -p -m755 %{buildroot}/usr/share/vpp/api

#
# configs
#
mkdir -p -m755 %{buildroot}/etc/vpp
mkdir -p -m755 %{buildroot}/etc/sysctl.d
install -p -m 644 %{_mu_build_dir}/../extras/rpm/vpp.service %{buildroot}%{_unitdir}
install -p -m 644 %{_mu_build_dir}/../src/vpp/conf/startup.conf %{buildroot}/etc/vpp/startup.conf
install -p -m 644 %{_mu_build_dir}/../src/vpp/conf/80-vpp.conf %{buildroot}/etc/sysctl.d
#
# libraries
#
mkdir -p -m755 %{buildroot}%{_libdir}
mkdir -p -m755 %{buildroot}/etc/bash_completion.d
mkdir -p -m755 %{buildroot}/usr/share/vpp
for file in $(find %{_mu_build_dir}/%{_vpp_install_dir}/*/lib* -type f -name '*.so.*.*' -print )
do
	install -p -m 755 $file %{buildroot}%{_libdir}
done
for file in $(cd %{buildroot}%{_libdir} && find . -type f -print | sed -e 's/^\.\///')
do
	# make lib symlinks
	( cd %{buildroot}%{_libdir} && 
          ln -fs $file $(echo $file | sed -e 's/\(\.so\.[0-9]\+\).*/\1/') )
	( cd %{buildroot}%{_libdir} && 
          ln -fs $file $(echo $file | sed -e 's/\(\.so\)\.[0-9]\+.*/\1/') )
done
for file in $(find %{_mu_build_dir}/%{_vpp_install_dir}/vpp/share/vpp/api  -type f -name '*.api.json' -print )
do
	install -p -m 644 $file %{buildroot}/usr/share/vpp/api
done

# Lua bindings
mkdir -p -m755 %{buildroot}/usr/share/doc/vpp/examples/lua/examples/cli
mkdir -p -m755 %{buildroot}/usr/share/doc/vpp/examples/lua/examples/lute
# for file in $(cd %{_mu_build_dir}/%{_vpp_install_dir}/../../src/vpp-api/lua && git ls-files .)
for file in $(cd %{_mu_build_dir}/%{_vpp_install_dir}/../../src/vpp-api/lua && find . -type f -regex '.*/*.[luteamd]' -print | sed -e 's/^\.\///')
do
	( cd %{_mu_build_dir}/%{_vpp_install_dir}/../../src/vpp-api/lua && install -p -m 644 $file \
	   %{buildroot}/usr/share/doc/vpp/examples/lua/$file )
done

# Python bindings
cd %{_mu_build_dir}/../src/vpp-api/python && %py3_install

# SELinux Policy
# Install SELinux interfaces
%_format INTERFACES %{_mu_build_dir}/../extras/selinux/$x.if
install -d %{buildroot}%{_datadir}/selinux/devel/include/%{moduletype}
install -p -m 644 $INTERFACES \
    %{buildroot}%{_datadir}/selinux/devel/include/%{moduletype}

# Install policy modules
%_format MODULES %{_mu_build_dir}/../extras/selinux/$x.pp
install -d %{buildroot}%{_datadir}/selinux/packages
install -m 0644 $MODULES \
    %{buildroot}%{_datadir}/selinux/packages

#
# devel
#
for dir in %{_mu_build_dir}/%{_vpp_install_dir}/vpp/include/
do
	for subdir in $(cd ${dir} && find . -type d -print)
	do
		mkdir -p -m755 %{buildroot}/usr/include/${subdir}
	done
	for file in $(cd ${dir} && find . -type f -print)
	do
		install -p -m 644 $dir/$file %{buildroot}%{_includedir}/$file
	done
done

install -p -m 644 %{_mu_build_dir}/../src/tools/vppapigen/vppapigen_c.py %{buildroot}/usr/share/vpp
install -p -m 644 %{_mu_build_dir}/../src/tools/vppapigen/vppapigen_json.py %{buildroot}/usr/share/vpp

# sample plugin
mkdir -p -m755 %{buildroot}/usr/share/doc/vpp/examples/sample-plugin/sample
#for file in $(cd %{_mu_build_dir}/%{_vpp_install_dir}/../../src/examples/sample-plugin && git ls-files .)
for file in $(cd %{_mu_build_dir}/%{_vpp_install_dir}/../../src/examples/sample-plugin && find . -type f -regex '.*/*.[acdhimp]' -print | sed -e 's/^\.\///')
do
	( cd %{_mu_build_dir}/%{_vpp_install_dir}/../../src/examples/sample-plugin && install -p -m 644 $file \
	   %{buildroot}/usr/share/doc/vpp/examples/sample-plugin/$file )
done

# vppctl sockfile directory
mkdir -p -m755 %{buildroot}%{_localstatedir}/run/vpp
# vpp.log directory
mkdir -p -m755 %{buildroot}%{_localstatedir}/log/vpp

#
# vpp-plugins
#
mkdir -p -m755 %{buildroot}/usr/%{_lib}/vpp_plugins
mkdir -p -m755 %{buildroot}/usr/%{_lib}/vpp_api_test_plugins
mkdir -p -m755 %{buildroot}/usr/%{_lib}/vat2_plugins
for file in $(cd %{_mu_build_dir}/%{_vpp_install_dir}/vpp/%{_lib}/vpp_plugins && find -type f -print)
do
        install -p -m 755 %{_mu_build_dir}/%{_vpp_install_dir}/vpp/%{_lib}/vpp_plugins/$file \
           %{buildroot}/usr/%{_lib}/vpp_plugins/$file
done

for file in $(cd %{_mu_build_dir}/%{_vpp_install_dir}/vpp/%{_lib}/vpp_api_test_plugins && find -type f -print)
do
        install -p -m 755 %{_mu_build_dir}/%{_vpp_install_dir}/vpp/%{_lib}/vpp_api_test_plugins/$file \
           %{buildroot}/usr/%{_lib}/vpp_api_test_plugins/$file
done

for file in $(cd %{_mu_build_dir}/%{_vpp_install_dir}/vpp/%{_lib}/vat2_plugins && find -type f -print)
do
        install -p -m 755 %{_mu_build_dir}/%{_vpp_install_dir}/vpp/%{_lib}/vat2_plugins/$file \
           %{buildroot}/usr/%{_lib}/vat2_plugins/$file
done

for file in $(find %{_mu_build_dir}/%{_vpp_install_dir}/vpp/share/vpp/api/plugins -type f -name '*.api.json' -print )
do
	install -p -m 755 $file %{buildroot}/usr/share/vpp/api
done

#
# remove RPATH from ELF binaries
#
%{_mu_build_dir}/scripts/remove-rpath %{buildroot}

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
%defattr(-,bin,bin)
%{_unitdir}/vpp.service
/usr/bin/vat2
/usr/bin/vpp*
/usr/bin/svm*
%config(noreplace) /etc/sysctl.d/80-vpp.conf
%config(noreplace) /etc/vpp/startup.conf
/usr/share/vpp/api/*

%defattr(-,root,vpp)
%{_localstatedir}/run/vpp*

%defattr(-,root,root)
%{_localstatedir}/log/vpp*

%files lib
%defattr(-,bin,bin)
%global __requires_exclude_from %{_libdir}/librte_pmd_mlx[45]_glue\\.so.*$
%exclude %{_libdir}/vpp_plugins
%exclude %{_libdir}/vpp_api_test_plugins
%exclude %{_libdir}/vat2_plugins
%{_libdir}/*
/usr/share/vpp/api/*

%files api-lua
%defattr(644,root,root,644)
/usr/share/doc/vpp/examples/lua

%files api-python3
%defattr(644,root,root,755)
%{python3_sitelib}/vpp_*

%files selinux-policy
%defattr(-,root,root,0755)
%attr(0644,root,root) %{_datadir}/selinux/packages/*.pp
%attr(0644,root,root) %{_datadir}/selinux/devel/include/%{moduletype}/*.if

%files devel
%defattr(-,bin,bin)
/usr/bin/vppapigen
/usr/bin/vapi_c_gen.py
/usr/bin/vapi_cpp_gen.py
/usr/bin/vapi_json_parser.py
%{_includedir}/*
/usr/share/doc/vpp/examples/sample-plugin
/usr/share/vpp

%files plugins
%defattr(-,bin,bin)
/usr/%{_lib}/vpp_plugins/
/usr/%{_lib}/vpp_api_test_plugins/
/usr/%{_lib}/vat2_plugins/
/usr/share/vpp/api/*
