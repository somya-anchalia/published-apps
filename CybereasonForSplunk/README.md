# Welcome to Cybereason for Splunk Apps documentation!

# Overview

## About Cybereason For Splunk

|                           |                                                             |
| ------------------------- | ----------------------------------------------------------- |
| Author                    | Metron Labs, Cybereason                                     |
| App Version               | 1.5.0                                                       |
| App Build                 | 184                                                         |
| Vendor Products           | Cybereason                                                  |
| Has index-time operations | true, the included TA add-on must be placed on the indexers |
| Creates an index          | false                                                       |
| Implements summarization  | Currently, the app does not generate summaries              |

About Cybereason For Splunk

Version 1.5.0 of Cybereason For Splunk is compatible with:

|                            |                   |
| -------------------------- | ----------------- |
| Splunk Enterprise versions | 8.2 or higher     |
| Platforms                  | Splunk Enterprise, Splunk Cloud |

Compatability

The Cybereason App for Splunk enables you to gain deep insight & visibility into your endpoints, detect advanced attacks based on AI hunting, and take response actions within Splunk. The Cybereason AI Hunting Engine automatically asks a complex set of questions of data collected from all of your endpoints at a rate of 8 million calculations per second, 24 hours a day, 7 days a week. This means the solution is continuously hunting on your behalf by asking the same sorts of questions advanced security analysts would ask as they hunt for threats inside an environment. The difference, however, is that the Cybereason malicious activity models run constantly, and continually adapt and evolve according to the data the solution receives and analyzes.

When the Cybereason AI Hunting Engine identifies malicious behavior, its classified based on context and severity. Suspicions represent multiple pieces of anomalous behavior which are related and therefore more likely to be malicious. Malops (malicious operations) are a collection of related suspicious activities that are highly likely to indicate a security incident, and are defined in a way that minimizes the likelihood of analysts spending time investigating benign activities or false positives. Both Suspicions and Malops are presented in Splunk along with insights that give context to the alerts so you can quickly understand what is happening in your environment.

## Scripts and binaries

This App provides the following scripts:

|                             |                                                                                 |
| --------------------------- | ------------------------------------------------------------------------------- |
| cybereason.py               | This python file controls the ability to interface with Cybereason.             |
| cybereason_rest_client.py | This Python class allows re-use of the cybereason api for various applications.   |
| Diag.py                     | Allows diag-targeted collection of information.                                 |
| ModularInput.py             | Inheritable Class to create Modular Inputs                                      |
| Utilities.py                | Allows utility interactions with Splunk Endpoints                               |

Scripts

# Release notes
## Version 1.5.0

  - Improvement
      - Upgraded dashboards to version 1.1 so that they work with Splunk Cloud 8.2
      
## Version 1.4.2

  - Improvement
      - Added suffix to child processes of Webshell malops for better identification
      - Handled an exception while fetching server info for User agent
      - Corrected the title of a panel in the Discovery board

## Version 1.4.1

  - Improvement
      - Better encryption facility for JWT authentication mode

## Version 1.4.0

  - Improvement
      - Comments are now included in the malop events
      - New filters for User Action Logs for better querying
      - Query enhancements for action logs
      - Logging improvement for successful login
  - Documentation
      - Added the steps to update credentials for an existing input

## Version 1.3.0

  - Feature
      - A new feature to turn off Logon Session data input from the User configuration settings
  - Improvement
      - Better error handling for processing events
      - Defined a new macro to query action logs in order to improve flexibility
  - Bug
      - Resolved some issues related to User action logs
      - Generating a new JWT token for authorization once the previous JWT has expired
      - Removed a duplicate About tab from the app configuration page

## Version 1.2.1

  - Improvement
      - The api headers is upadted to contain User-agent detail which will include the application version and server address
      - The app now has the capability to log stacktrace if any exception occurs
      - User action logs are downloaded in the log directory path and removed after they have been processed

## Version 1.2.0

  - Enhancement
      - Enabled the global field extraction for the app
      - Added the action field for malop and malware events so that events get tagged correctly by the malware data model

## Version 1.1.3

  - Bug
      - Added a validation while fetching child processes for webshell typed malops

## Version 1.1.2

  - Bug
      - Minor change in the event type of the User audit log filter

## Version 1.1.1

  - Improvement
      - User action logs can now be configured using User Activity Input button which has a default interval of 24h as it has a significant footprint

## Version 1.0.6

  - Enhancements
      - User Activity Input button for polling users data with default interval time of 24 hours. 
      - All new dashboard to monitor action logs
      - Severity values for Malop inbox table
      - Option to authenticate using JWT token
      - Removed troubleshooting logs to make the app space efficient
      - Authentication data model to keep track of user log-ins once every 24h
      - Webshell malop will now contain all of the child processes (and their children, and so on)
  - Bug
      - Fixed duplicate malwares bug to make the app more memory efficienct
      - Resolved broken pipe error that obstructed the app's execution sometimes
      - Added missing validations to improve application workflow

## Version 1.0.5

  - Improvement
    
      - Splunk Cloud Updates

## Version 1.0.4

  - Bug
    
      - [CYB-66] - Login Routine causes cmp recursion

## Version 1.0.3

  - Bug
    
      - [DESK-710] - Add code to disregard comments field on malops events
    
      - [DESK-716] - Fix paging issue with malware events

## Version 1.0.2

  - Bug
    
      - [CYB-41] - IA shipped with no log.cfg
    
      - [CYB-43] - Remove URL inspection
    
      - [DESK-681] - Convert From All Suspicions To time_bound

  - Improvement
    
      - [CYB-39] - Update versioned API call
    
      - [CYB-42] - Malware Endpoint Change
    
      - [CYB-44] - Better Handling of HTML Error Messages
    
      - [CYB-45] - Improper Pagination on >17.5 API Calls
    
      - [DESK-663] - Last Activity Sorting is Incorrect
    
      - [DESK-664] - Classification Type And File Path Fields Are Empty For Powershell
    
      - [DESK-665] - Change Default Time Filter To Last 30 Days
    
      - [DESK-666] - Suspicious Insights Tab Not Functioning
    
      - [DESK-667] - Malop Inbox - Malop Type And Hashes Are Empty For Blacklisted IP
    
      - [DESK-668] - Malop Inbox - Sort by Last Activity Desc - Malops From Previous Year Are Presented First
    
      - [DESK-669] - Malop Inbox - Multiple Values For Affected Machines
    
      - [DESK-670] - Malop Inbox - File Hashes Section Is Empty For Obscured Extension Malop
    
      - [DESK-671] - Malop Inbox - Malop Type Is Empty For Custom Rule Malop
    
      - [DESK-672] - Malop Inbox - Malop Type Is Empty For Pass The Hash Malop
    
      - [DESK-700] - Malware Inbox - Unknown And App Control Malware Are Not Presented At Inbox
    
      - [DESK-701] - Malware Inbox - Fileless Malware Data Is Not Presented For Last Month
    
      - [DESK-702] - Malware Inbox - Multiple Values For Scan Time
    
      - [DESK-703] - Malop Statistics - Machine Data Discrepancy
    
      - [DESK-704] - Malop Statistics - Users And Files Data Discrepancy
    
      - [DESK-706] - Malop Inbox - Long Process List Breaks The Layout

## Version 1.0.1

  - Bug
    
      - [CYB-38] - Cloud Vetting

## Version 1.0.0

  - Test and QA
    
      - [CYB-27] - Failed Test - Evengent Docs

  - Bug
    
      - [CYB-13] - Remove Proxy Configs for Mod Inputs
    
      - [CYB-24] - Modular Input throwing 400 errors
    
      - [CYB-32] - More UI Changes
    
      - [CYB-34] - Counting of Fields
    
      - [CYB-35] - Enable Proxy configurations
    
      - [CYB-36] - Self Signed Certificate throws error on request
    
      - [CYB-37] - API Inconsistent - Throws exception on string boolean

  - New Feature
    
      - [CYB-6] - Modular Input
    
      - [CYB-7] - Field Extractions and CIM Compliance
    
      - [CYB-8] - Discovery Dashboard
    
      - [CYB-9] - Inbox Dashboard
    
      - [CYB-10] - Malop Breakdown Dashboard
    
      - [CYB-11] - Malware Dashboard
    
      - [CYB-12] - Suspicions Dashboard
    
      - [CYB-14] - Malops Breakdown - Additional detail
    
      - [CYB-15] - App Icons
    
      - [CYB-17] - Health Dashboard
    
      - [CYB-26] - Create Eventgen

  - Improvement
    
      - [CYB-16] - Discovery Dashboard Modifications
    
      - [CYB-18] - Inbox Dashboard Cell Drilldown
    
      - [CYB-20] - Add Host Dropdown - All Dashboards
    
      - [CYB-22] - Remove Menu Slider
    
      - [CYB-23] - Discovery Board
    
      - [CYB-25] - Suspicions Inbox Update searches
    
      - [CYB-28] - Slight Updates
    
      - [CYB-29] - CSS Changes
    
      - [CYB-30] - Updates to Interface

## Known Issues

Version 1.0.5 of Cybereason For Splunk has the following known issues:

  - None

# Support and resources

## Questions and answers

Access questions and answers specific to Cybereason For Splunk at [https://answers.splunk.com](https://answers.splunk.com) . Be sure to tag your question with the App.

## Support

  - Support Email: [support@cybereason.com](mailto:support%40cybereason.com)

  - Support Offered: Email, Community Engagement

Support is available via email at [support@cybereason.com](mailto:support%40cybereason.com).

# Installation and Configuration

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements]([https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements)) apply.

## Download

Download Cybereason For Splunk at [https://splunkbase.splunk.com](https://splunkbase.splunk.com).

## Installation steps

NOTE: Where referenced, the IA-CybereasonForSplunk and TA-CybereasonForSplunk versions of this App are located on Splunkbase.

### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Deploy as you would any App, and restart Splunk.

2.  Install IA-CybereasonForSplunk.

3.  Configure.

### Deploy to Splunk Cloud

1.  Have your Splunk Cloud Support handle this installation. Do NOT install the IA on the same system as the App.

2.  You may consider using an on-premise Heavy Forwarder to install IA-CybereasonForSplunk, and send the logs to Splunk Cloud.

### Deploy to a Distributed Environment

1.  For each Search Head in the environment, deploy a non-configured copy of the App. DO NOT SEND TA or IA to a Search Head Cluster (SHC).

2.  For each indexer in the environment, deploy a copy of the TA-CybereasonForSplunk Add-On that is located as mentioned above.

3.  For a single Data Collection Node OR Heavy Forwarder (a full instance of Splunk is required), install IA-CybereasonForSplunk and configure through the GUI.

# User Guide

## Configure Cybereason For Splunk

  - Install the App according to your environment (see steps above)

  - Navigate to App > IA-CybereasonForSplunk > Administration > Application Configuration

### Application Configuration Dashboard

To configure the Cybereason application you should start on the Application Configuration page (Administration > Application Configuration)\*[]:

### Application Configuration

On this screen you can set the base index via event type as well as indicating that you have configured the app. Make sure you click the *SAVE* button to access the additional dashboards.

### Encrypted Credentials

You can view/delete existing credentials on this tab. These are credentials that are being used by existing modular inputs in the Cybereason application. These credentials are the credentials used to connect to Cybereason appliances.

### Cybereason

On this screen you can view and make any changes to existing modular inputs. As you make changes and tab between fields the modular input is modified.

### Creating New Cybereason Inputs

**NOTE:** You will need to configure a new modular input for each Cybereason host.

**NOTE:** The Suspicious data type should be only pulled 1 once per day. This particular input pulls all available suspicious items, *not* just the time-based delta, at the time of ingest. Please configure a separate input with interval 600 for the suspicious data type.

  - To create a new data input, click the Create New Cybereason Input button and fill in the following fields. Those with a red asterisk on the screen are required.
    
      - Modular Input Name: Name for the data input configuration.
    
      - Base URL: The hostname or IP address and port of the Cybereason service. By default you can specify hostname:443.
    
      - Username: The username used to connect to the service.
    
      - Password: The password for the previously specified service.
    
      - Toggle all data keys: Check to select all data keys.
    
      - Data keys: List of endpoints available on the Cybereason service. Check the data key if you wish to pull event data.
    
      - Interval: The number of seconds indicate how often the input will poll for new data. This setting must be at least 60.
    
      - Index: This sets the index for data to be written to. This setting should be changed from default, which normally writes to the main index, to a specified index for best performance. The index must exist on the Search Head and Indexer.

  - After creating the modular input you may need to disable/re-enable the input in Settings > Data Inputs > Cybereason For Splunk to activate the input.

**NOTE:** When configuring the modular input through the Application Configuration dashboard, the password is automatically encrypted into the credential store. If you need to change the credential, create a new credential, and reference the host/user pair in the modular input configuration. An encrypted credential is required for this Splunk App.


### Creating New Credentials

By default creating a new modular input with a username and password specified will create the necessary encrypted credentials. However if you want to create encrypted credentials manually follow this process:

  - Navigate to the Credentials tab.

  - To create a new encrypted credential, click the Create New Credential button and fill in with the appropriate username and password.

  - The realm is the application name where the encrypted credential is created + the username.

*NOTE: By default creating a new modular input will automatically create a new encrypted credential so this process is not necessary unless you need a new credential for another purpose.*

### Updating Existing Credentials

If you want to update existing credentials manually follow this process:

  - Navigate to the “Cybereason” tab.

  - Copy the Credential Realm of the Input for which credentials have to be updated.

  - Navigate to the “Credential” tab.

  - Search for the Credential using the copied Credential Realm.

  - Delete the existing Credential of that Credential Realm using the delete button.

  - To update credential, click the Create New Credential button and fill in with the appropriate information below:

      - Username (The username of the configured input)
      - Password (The new password for that username) 
      - Realm (Credential Realm of the configured input)


## Indexes

By default all events will be written to the main index. You should change the index in the configuration files to match your specific index.

## Troubleshoot Cybereason For Splunk

1.  Check the Monitoring Console (>=v6.5) for errors

2.  Visit the Application Health dashboard

3.  Check for errors using following queries:
```
index=_internal sourcetype=modularinput OR sourcetype=restclient log_level=ERROR
```
```
index=<yourindex> sourcetype=CyberreasonForSplunk:error`
```

4.  Execute `$SPLUNK_HOME/bin/splunk diag --collect app:CybereasonForSplunk` and send the diag to Cybereason Support.

## Lookups

Cybereason For Splunk contains the following lookup files.

  - labels.csv - contains the labels for use with the Cybereason data

  - malop_types.csv - a lookup that helps drive panels

## Event Generator

Cybereason For Splunk does make use of an event generator. This allows the product to display data, when there are no inputs configured. Each input listed below must be enabled locally. They are disabled by default.

You can access the eventgen configuration tab in the Application Configuration dashboard.

  - cybereason_users.sample

  - cybereason_malops_rootCauseElements.sample

  - cybereason_malware.sample

  - cybereason_malops_affectedUsers.sample

  - cybereason_malops_filesToRemediate.sample

  - cybereason_malop.sample

  - cybereason_malops_suspects.sample

  - cybereason_malops_affectedMachines.sample

  - cybereason_suspicious.sample

## Acceleration

1.  Summary Indexing: No

2.  Data Model Acceleration: No

3.  Report Acceleration: No

# Third Party Notices

Version 1.0.5 of Cybereason For Splunk incorporates the following Third-party software or third-party services.

## Metron Labs

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, eMA 02110-1301, USA.

## defusedxml

## defusedxml

PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2

1\. This LICENSE AGREEMENT is between the Python Software Foundation (PSF), and the Individual or Organization (Licensee) accessing and otherwise using this software (Python) in source or binary form and its associated documentation.

2\. Subject to the terms and conditions of this License Agreement, PSF hereby grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce, analyze, test, perform and/or display publicly, prepare derivative works, distribute, and otherwise use Python alone or in any derivative version, provided, however, that PSFs License Agreement and PSFs notice of copyright, i.e., Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008 Python Software Foundation; All Rights Reserved are retained in Python alone or in any derivative version prepared by Licensee.

3\. In the event Licensee prepares a derivative work that is based on or incorporates Python or any part thereof, and wants to make the derivative work available to others as provided herein, then Licensee hereby agrees to include in any such work a brief summary of the changes made to Python.

4\. PSF is making Python available to Licensee on an AS IS basis. PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED. BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.

5\. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON, OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6\. This License Agreement will automatically terminate upon a material breach of its terms and conditions.

7\. Nothing in this License Agreement shall be deemed to create any relationship of agency, partnership, or joint venture between PSF and Licensee. This License Agreement does not grant permission to use PSF trademarks or trade name in a trademark sense to endorse or promote products or services of Licensee, or any third party.

8\. By copying, installing or otherwise using Python, Licensee agrees to be bound by the terms and conditions of this License Agreement.

## markdown.js

Released under the MIT license.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the Software), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## jquery.js

[https://github.com/jquery/jquery/blob/master/LICENSE.txt](https://github.com/jquery/jquery/blob/master/LICENSE.txt)

Copyright JS Foundation and other contributors, [https://js.foundation/](https://js.foundation/)

This software consists of voluntary contributions made by many individuals. For exact contribution history, see the revision history available at [https://github.com/jquery/jquery](https://github.com/jquery/jquery)

The following license applies to all parts of this software except as documented below:

-----

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the Software), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

-----

All files located in the node_modules and external directories are externally maintained libraries used by this software which have their own licenses; we recommend you read them, as their terms may differ from the terms above.

## d3.js

[https://github.com/d3/d3/blob/master/LICENSE](https://github.com/d3/d3/blob/master/LICENSE)

Copyright 2010-2016 Mike Bostock All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

  - Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

  - Neither the name of the author nor the names of contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS AS IS AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# [Cybereason For Splunk](#)

### Navigation

### Related Topics

  - [Documentation overview](#)

2021, Metron Labs
