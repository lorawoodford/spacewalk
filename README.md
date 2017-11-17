# spacewalk
DSpace to ASpace crosswalking for JHU

We have **DSpace** items with bitstreams filenames like:
  * 01_01_22_33.pdf
  
That needed to be matched to **ASpace** archival objects with instance information like:
  * Box 1-1
  * Folder 22
  * Item 33
  
No other possible match point existed between the DSpace digital surrogates and the ASpace archival objects.  This script does the heavy lifting.

While our situation is unique (and, notably, not IDEAL!), the idea of yanking DSpace handles/bitstreams out with the DSpace (in our case v. 5) API, comparing to ASpace archival objects with the ASpace API (for us, v. 1.5.4), and posting new digital objects back in to ASpace with the API is a repurposable activities others may want to investigate.  So, your specifics will vary, but the basics may stay largely the same!
