"use client";

import { useState, useRef, useEffect } from "react";
import { Icon } from "@/components/shared/Icon";

export interface CustomSelectOption {
  value: string;
  label: string;
}

export interface CustomSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: CustomSelectOption[];
  className?: string;
}

export function CustomSelect({ value, onChange, options, className = "" }: CustomSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isPressed, setIsPressed] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((o) => o.value === value) || options[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className={`relative inline-block text-left ${className}`} ref={ref}>
      <button
        type="button"
        onMouseDown={() => setIsPressed(true)}
        onMouseUp={() => setIsPressed(false)}
        onMouseLeave={() => setIsPressed(false)}
        onClick={() => setIsOpen(!isOpen)}
        className={`flex h-[46px] items-center justify-between rounded-full border-[1.5px] bg-white text-[16px] font-semibold shadow-sm transition-all focus:outline-none ${isOpen
          ? "border-[#c4b5fd] ring-4 ring-[#ddd6fe]/40"
          : "border-[#c4b5fd] hover:border-[#a78bfa]"
          }`}
        style={{ minWidth: "260px" }}
      >
        <span className="truncate px-5 text-[#1e1e24]">{selectedOption?.label}</span>
        <div
          className={`flex h-full w-[32px] shrink-0 items-center justify-center transition-colors ${isPressed ? " rounded-r-full" : ""
            }`}
        >
          <Icon
            name="chevron"
            size={16}
            style={{
              color: "#6b7280",
              transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.2s ease",
            }}
          />
        </div>
      </button>

      {isOpen && (
        <div className="absolute right-0 z-50 mt-1.5 w-full origin-top-right overflow-hidden rounded-[20px] bg-white border-[1.5px] border-[#c4b5fd] shadow-lg focus:outline-none">
          <div className="flex flex-col py-1 max-h-[250px] overflow-y-auto">
            {options.map((option, index) => (
              <div key={option.value}>
                <button
                  type="button"
                  onClick={() => {
                    onChange(option.value);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left px-5 py-3 text-[16px] transition-colors hover:bg-gray-50 ${value === option.value
                    ? "font-bold text-[#1f2937]"
                    : "font-medium text-[#374151]"
                    }`}
                >
                  {option.label}
                </button>
                {index < options.length - 1 && <div className="mx-4 h-px bg-gray-100" />}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}