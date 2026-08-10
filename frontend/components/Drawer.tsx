import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  statusBadge?: React.ReactNode;
  children: React.ReactNode;
}

export function Drawer({ isOpen, onClose, title, statusBadge, children }: DrawerProps) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleEsc);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleEsc);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 z-40 bg-[rgba(25,5,22,0.60)] backdrop-blur-sm transition-opacity duration-300"
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Drawer */}
      <div 
        className="fixed inset-y-0 right-0 z-50 w-full md:w-[500px] lg:w-[600px] bg-cream-50 shadow-elevated transform transition-transform duration-300 ease-in-out"
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="bg-plum-900 text-cream-50 p-6 flex flex-col gap-2 shrink-0">
            <div className="flex justify-between items-start">
              <h2 id="drawer-title" className="font-serif text-2xl font-normal text-cream-50 m-0">
                {title}
              </h2>
              <button 
                onClick={onClose}
                className="text-cream-50/70 hover:text-cream-50 transition-colors p-1 rounded-full hover:bg-white/10"
                aria-label="Close"
              >
                <X size={24} />
              </button>
            </div>
            {statusBadge && (
              <div className="mt-2">
                {statusBadge}
              </div>
            )}
          </div>
          
          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 text-text-primary">
            {children}
          </div>
        </div>
      </div>
    </>
  );
}
