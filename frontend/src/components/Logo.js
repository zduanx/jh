function Logo({ size = 32, collapsed = false }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ minWidth: size, minHeight: size }}
    >
      {/* Background Circle */}
      <circle cx="24" cy="24" r="22" fill="url(#gradient1)" />

      {/* Briefcase Icon */}
      <path
        d="M32 16H30V14C30 12.897 29.103 12 28 12H20C18.897 12 18 12.897 18 14V16H16C14.897 16 14 16.897 14 18V32C14 33.103 14.897 34 16 34H32C33.103 34 34 33.103 34 32V18C34 16.897 33.103 16 32 16ZM20 14H28V16H20V14ZM32 32H16V24H32V32ZM32 22H16V18H32V22Z"
        fill="white"
      />

      {/* Checkmark overlay */}
      <circle cx="34" cy="34" r="7" fill="#10b981" />
      <path
        d="M31.5 34L33.5 36L36.5 32"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Gradient Definition */}
      <defs>
        <linearGradient id="gradient1" x1="24" y1="2" x2="24" y2="46" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#60a5fa" />
          <stop offset="100%" stopColor="#3b82f6" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default Logo;
