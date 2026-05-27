// Lucide-style icon set (1.5px stroke, 24 viewBox). Inline so kit works offline.

const Ic = ({ d, size = 16, sw = 1.5, ...rest }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" {...rest}>
    {d}
  </svg>
);

const IconBriefcase = (p) => <Ic {...p} d={<><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></>}/>;
const IconTarget = (p) => <Ic {...p} d={<><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></>}/>;
const IconBookmark = (p) => <Ic {...p} d={<path d="m19 21-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>}/>;
const IconClock = (p) => <Ic {...p} d={<><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></>}/>;
const IconArrowUpRight = (p) => <Ic {...p} d={<path d="M7 17 17 7M17 7H7M17 7v10"/>}/>;
const IconExternalLink = (p) => <Ic {...p} d={<><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></>}/>;
const IconSliders = (p) => <Ic {...p} d={<><line x1="4" x2="4" y1="21" y2="14"/><line x1="4" x2="4" y1="10" y2="3"/><line x1="12" x2="12" y1="21" y2="12"/><line x1="12" x2="12" y1="8" y2="3"/><line x1="20" x2="20" y1="21" y2="16"/><line x1="20" x2="20" y1="12" y2="3"/><line x1="2" x2="6" y1="14" y2="14"/><line x1="10" x2="14" y1="8" y2="8"/><line x1="18" x2="22" y1="16" y2="16"/></>}/>;
const IconSearch = (p) => <Ic {...p} d={<><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></>}/>;
const IconSettings = (p) => <Ic {...p} d={<><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></>}/>;
const IconBell = (p) => <Ic {...p} d={<><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></>}/>;
const IconCheck = (p) => <Ic {...p} d={<polyline points="20 6 9 17 4 12"/>}/>;
const IconCheckCircle = (p) => <Ic {...p} d={<><circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 9"/></>}/>;
const IconCircle = (p) => <Ic {...p} d={<circle cx="12" cy="12" r="10"/>}/>;
const IconX = (p) => <Ic {...p} d={<><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></>}/>;
const IconChevronLeft = (p) => <Ic {...p} d={<polyline points="15 18 9 12 15 6"/>}/>;
const IconChevronRight = (p) => <Ic {...p} d={<polyline points="9 18 15 12 9 6"/>}/>;
const IconChevronDown = (p) => <Ic {...p} d={<polyline points="6 9 12 15 18 9"/>}/>;
const IconPlus = (p) => <Ic {...p} d={<><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></>}/>;
const IconLayers = (p) => <Ic {...p} d={<><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></>}/>;
const IconMapPin = (p) => <Ic {...p} d={<><path d="M20 10c0 7-8 12-8 12s-8-5-8-12a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/></>}/>;
const IconBanknote = (p) => <Ic {...p} d={<><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></>}/>;
const IconGlobe = (p) => <Ic {...p} d={<><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></>}/>;
const IconHome = (p) => <Ic {...p} d={<><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></>}/>;
const IconBuilding = (p) => <Ic {...p} d={<><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01"/></>}/>;
const IconCalendar = (p) => <Ic {...p} d={<><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></>}/>;
const IconStar = (p) => <Ic {...p} d={<polygon points="12 2 15.1 8.6 22 9.5 17 14.5 18.2 21.5 12 18.2 5.8 21.5 7 14.5 2 9.5 8.9 8.6"/>}/>;
const IconTrendingUp = (p) => <Ic {...p} d={<><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></>}/>;
const IconSparkle = (p) => <Ic {...p} d={<><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/></>}/>;
const IconBolt = (p) => <Ic {...p} d={<polygon points="13 2 3 14 12 14 11 22 21 10 12 10"/>}/>;
const IconArchive = (p) => <Ic {...p} d={<><rect x="2" y="3" width="20" height="5" rx="1"/><path d="M4 8v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/></>}/>;
const IconUser = (p) => <Ic {...p} d={<><circle cx="12" cy="8" r="4"/><path d="M4 22a8 8 0 0 1 16 0"/></>}/>;
const IconDot = (p) => <Ic {...p} d={<circle cx="12" cy="12" r="4" fill="currentColor"/>} sw={0}/>;

Object.assign(window, {
  IconBriefcase, IconTarget, IconBookmark, IconClock, IconArrowUpRight, IconExternalLink,
  IconSliders, IconSearch, IconSettings, IconBell, IconCheck, IconCheckCircle, IconCircle, IconX,
  IconChevronLeft, IconChevronRight, IconChevronDown, IconPlus, IconLayers, IconMapPin,
  IconBanknote, IconGlobe, IconHome, IconBuilding, IconCalendar, IconStar, IconTrendingUp,
  IconSparkle, IconBolt, IconArchive, IconUser, IconDot
});
