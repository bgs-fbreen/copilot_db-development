-- ============================================================================
-- Migration 008: Add notes column to vendor_gl_patterns
-- Created: 2025-12-30
-- Purpose: Support storing user notes/context for pattern assignments
-- ============================================================================

-- Add notes column if it doesn't exist (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'acc' 
          AND table_name = 'vendor_gl_patterns' 
          AND column_name = 'notes'
    ) THEN
        ALTER TABLE acc.vendor_gl_patterns ADD COLUMN notes TEXT;
        RAISE NOTICE 'Added notes column to acc.vendor_gl_patterns';
    ELSE
        RAISE NOTICE 'Column notes already exists in acc.vendor_gl_patterns';
    END IF;
END $$;
