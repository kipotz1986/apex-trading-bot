"use client"

import React from "react"
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown, Loader2, XCircle } from "lucide-react"
import { useOpenPositions, useClosePosition } from "@/hooks/useApi"
import { useWebSocket } from "@/hooks/useWebSocket"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { OpenPosition } from "@/types/api"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

export function PositionsTable() {
  const { data: initialPositions, isLoading } = useOpenPositions();
  const [positions, setPositions] = React.useState<OpenPosition[]>([]);
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [selectedPos, setSelectedPos] = React.useState<OpenPosition | null>(null);
  
  const closeMutation = useClosePosition();

  // Initialize positions from API
  React.useEffect(() => {
    if (initialPositions) {
      setPositions(initialPositions);
    }
  }, [initialPositions]);

  // Handle Real-time Position Updates (Open/Close)
  useWebSocket("position_update", (data: any) => {
    if (data.type === "opened") {
      setPositions(prev => {
        if (prev.some(p => p.id === data.position.id)) return prev;
        toast.success(`Position opened: ${data.position.symbol} ${data.position.side}`);
        return [data.position, ...prev];
      });
    } else if (data.type === "closed") {
      setPositions(prev => {
        const exists = prev.some(p => p.id === data.position_id);
        if (exists) {
          toast.info(`Position closed: ${data.symbol}`);
        }
        return prev.filter(p => p.id !== data.position_id);
      });
    }
  });

  // Handle Real-time Market Prices via WebSocket
  useWebSocket("market_prices", (data: {symbol: string, price: number}) => {
    setPositions(prev => prev.map(p => {
      // Normalize symbols for comparison (e.g. BTC/USDT vs BTC/USDT:USDT)
      const normalize = (s: string) => s.split(':')[0].replace('/', '').toUpperCase();
      
      if (normalize(p.symbol) === normalize(data.symbol)) {
        const newPrice = data.price;
        const isLong = p.side === 'LONG' || p.side === 'BUY';
        
        // Safety check to avoid division by zero / Infinity
        if (!p.entry || p.entry <= 0) {
          return {
            ...p,
            current: newPrice,
            pnl: 0,
            pnl_percent: 0
          } as OpenPosition;
        }

        const pnl = (newPrice - p.entry) * p.size * (isLong ? 1 : -1);
        const pnl_pct = (newPrice / p.entry - 1) * 100 * p.leverage * (isLong ? 1 : -1);
        
        return {
          ...p,
          current: newPrice,
          pnl: pnl,
          pnl_percent: pnl_pct,
          status: pnl >= 0 ? 'profit' : 'loss'
        } as OpenPosition;
      }
      return p;
    }));
  });

  const handleCloseClick = (pos: OpenPosition) => {
    setSelectedPos(pos);
    setConfirmOpen(true);
  };

  const handleConfirmClose = async () => {
    if (!selectedPos) return;
    
    try {
      const orderId = selectedPos.id;
      await closeMutation.mutateAsync(orderId);
      toast.success(`Closing position for ${selectedPos.symbol}...`);
      setPositions(prev => prev.filter(p => p.id !== selectedPos.id));
      setConfirmOpen(false);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to close position");
    }
  };

  if (isLoading && positions.length === 0) {
    return (
      <div className="p-8 space-y-4">
        {[1, 2, 3].map(i => (
          <Skeleton key={i} className="h-12 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (!isLoading && positions.length === 0) {
    return (
      <div className="p-12 text-center space-y-2">
        <p className="text-sm font-bold text-muted-foreground uppercase tracking-widest">No Active Positions</p>
        <p className="text-[10px] text-muted-foreground/60 font-medium">Bot is currently scanning for entry signals.</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <Table>
        <TableHeader className="bg-muted/20 border-y border-border/50">
          <TableRow className="border-none hover:bg-transparent">
            <TableHead className="text-[10px] font-bold text-muted-foreground/80 uppercase tracking-widest pl-8">Symbol</TableHead>
            <TableHead className="text-[10px] font-bold text-muted-foreground/80 uppercase tracking-widest text-center">Side</TableHead>
            <TableHead className="text-[10px] font-bold text-muted-foreground/80 uppercase tracking-widest">Position Size</TableHead>
            <TableHead className="text-[10px] font-bold text-muted-foreground/80 uppercase tracking-widest">Entry / Mark</TableHead>
            <TableHead className="text-[10px] font-bold text-muted-foreground/80 uppercase tracking-widest">Unrealized PnL</TableHead>
            <TableHead className="text-[10px] font-bold text-muted-foreground/80 uppercase tracking-widest text-right pr-8">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {positions.map((pos) => {
            const isLong = pos.side === 'LONG' || pos.side === 'BUY';
            return (
              <TableRow key={pos.id} className="border-b border-border/50 hover:bg-muted/20 transition-colors group">
                <TableCell className="py-5 pl-8">
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-foreground tracking-tight">{pos.symbol}</span>
                    <span className="text-[10px] text-muted-foreground/60 font-medium">{pos.symbol.includes(':') ? 'Perpetual' : 'Spot'}</span>
                  </div>
                </TableCell>
                
                <TableCell className="text-center">
                  <Badge className={cn(
                    "px-2 py-0.5 rounded text-[9px] font-black tracking-widest uppercase",
                    isLong ? "bg-primary/10 text-primary" : "bg-red-500/10 text-red-500"
                  )}>
                    {pos.side}
                  </Badge>
                </TableCell>
                
                <TableCell>
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-foreground">{pos.size} {pos.symbol.split('/')[0]}</span>
                      <Badge variant="outline" className="text-[9px] text-muted-foreground/80 border-border/50 px-1.5 h-4">
                        {pos.leverage}x
                      </Badge>
                    </div>
                    <span className="text-[10px] text-muted-foreground/60 font-medium">
                      ${(pos.size * (pos.entry > 0 ? pos.entry : pos.current)).toLocaleString(undefined, {minimumFractionDigits: 2})}
                    </span>
                  </div>
                </TableCell>
                
                <TableCell>
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-foreground tracking-tighter">
                      {pos.entry > 0 
                        ? `$${pos.entry.toLocaleString(undefined, {minimumFractionDigits: 2})}` 
                        : "PENDING"}
                    </span>
                    <span className={cn(
                      "text-[10px] font-medium tracking-tighter transition-colors duration-500",
                      pos.current !== pos.entry ? "text-primary/80" : "text-muted-foreground/80"
                    )}>
                      ${pos.current.toLocaleString(undefined, {minimumFractionDigits: 2})}
                    </span>
                  </div>
                </TableCell>
                
                <TableCell>
                  {pos.entry > 0 && pos.pnl_percent !== null && isFinite(pos.pnl_percent) ? (
                    <div className={cn(
                      "flex items-center gap-1.5 text-xs font-bold transition-all duration-300",
                      pos.status === 'profit' ? "text-primary" : "text-red-500"
                    )}>
                      {pos.status === 'profit' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {pos.pnl >= 0 ? '+' : ''}{pos.pnl.toFixed(2)} ({pos.pnl_percent.toFixed(2)}%)
                    </div>
                  ) : (
                    <span className="text-[10px] text-muted-foreground/60 font-medium">Calculating...</span>
                  )}
                </TableCell>
                
                <TableCell className="text-right pr-8">
                   <button 
                    onClick={() => handleCloseClick(pos)}
                    disabled={closeMutation.isPending}
                    className="text-[10px] font-bold text-muted-foreground/60 hover:text-red-400 disabled:opacity-50 transition-colors uppercase tracking-widest flex items-center gap-1.5 ml-auto"
                   >
                     {closeMutation.isPending && selectedPos?.id === pos.id ? (
                       <Loader2 className="w-3 h-3 animate-spin" />
                     ) : (
                       <XCircle className="w-3 h-3" />
                     )}
                     Close
                   </button>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {/* Confirmation Dialog */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="bg-card border-border text-foreground max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold tracking-tight">Close Position?</DialogTitle>
            <DialogDescription className="text-muted-foreground text-xs">
              Are you sure you want to close your <span className="text-foreground font-bold">{selectedPos?.side}</span> position for <span className="text-foreground font-bold">{selectedPos?.symbol}</span> at market price?
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-3">
            <div className="flex justify-between items-center p-3 rounded-lg bg-muted/20 border border-border/50">
              <span className="text-[10px] font-bold text-muted-foreground/80 uppercase tracking-widest">Unrealized PnL</span>
              <span className={cn(
                "text-xs font-black",
                (selectedPos?.pnl || 0) >= 0 ? "text-primary" : "text-red-500"
              )}>
                {(selectedPos?.pnl ?? 0) >= 0 ? '+' : ''}{selectedPos?.pnl?.toFixed(2) ?? '0.00'} USD
              </span>
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button 
              variant="ghost" 
              onClick={() => setConfirmOpen(false)}
              className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground hover:text-foreground"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleConfirmClose}
              disabled={closeMutation.isPending}
              className="bg-red-500 hover:bg-red-600 text-foreground text-[10px] font-black uppercase tracking-widest"
            >
              {closeMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-2" /> : null}
              Confirm Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
