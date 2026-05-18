interface DividerToggleProps {
  sourcesVisible: boolean;
  onClick: () => void;
}

// Parent container must have `position: relative` for absolute positioning to anchor correctly.
export function DividerToggle({ sourcesVisible, onClick }: DividerToggleProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="hidden md:flex pointer-events-none md:pointer-events-auto absolute z-10 items-center justify-center text-[#6b4e35] cursor-pointer transition-colors hover:text-[#4a3728]"
      style={{
        top: '50%',
        transform: sourcesVisible ? 'translate(-50%, -50%)' : 'translateY(-50%)',
        left: sourcesVisible ? '50%' : undefined,
        right: sourcesVisible ? undefined : 0,
        width: 18,
        height: 36,
        background: '#faf9f7',
        border: '1.5px solid #6b4e35',
        borderRadius: sourcesVisible ? '10px' : '8px 0 0 8px',
        fontSize: 11,
        boxShadow: '0 1px 4px rgba(107,78,53,0.15)',
      }}
      aria-label={sourcesVisible ? 'Collapse sources' : 'Expand sources'}
    >
      {sourcesVisible ? '›' : '‹'}
    </button>
  );
}
