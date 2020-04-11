let mapleader = '-'

call plug#begin('~/.nvim/plugged')
Plug 'tpope/vim-surround'
Plug 'tpope/vim-fugitive' "  git
Plug 'jreybert/vimagit' "  git
Plug 'tpope/vim-commentary'
Plug 'tpope/vim-eunuch'
Plug 'scrooloose/nerdtree'
Plug 'vim-airline/vim-airline'
Plug 'vim-airline/vim-airline-themes'
Plug 'pangloss/vim-javascript' "  syntax
Plug 'leafgarland/typescript-vim' "  syntax
Plug 'tpope/vim-cucumber'  "  syntax
Plug '/usr/local/opt/fzf'
Plug 'junegunn/fzf.vim'
Plug 'Shougo/deoplete.nvim', { 'do': ':UpdateRemotePlugins' }
Plug 'SirVer/ultisnips' "  completions
Plug 'honza/vim-snippets'
Plug 'deoplete-plugins/deoplete-jedi' "  completions
Plug 'carlitux/deoplete-ternjs' " completions
" Plug 'python-mode/python-mode', { 'branch': 'master' }
Plug 'chrisbra/csv.vim'
"
call plug#end()

nnoremap <leader><C-f> :FZF<CR>

" vim-airline
let g:airline#extensions#ale#enabled = 1

" fzf
set rtp+=$HOME/.fzf/

" nerdtree
nnoremap <leader><C-n> :NERDTreeToggle<CR>

" ale
let g:ale_lint_on_text_changed = 'never'

" deoplete
let g:deoplete#enable_at_startup = 1
" autoclose Preview buffer
" autocmd InsertLeave,CompleteDone * if pumvisible() == 0 | pclose | endif

" ultisnips
let g:UltiSnipsExpandTrigger='<c-k>'
let g:UltiSnipsJumpForwardTrigger='<c-b>'
let g:UltiSnipsJumpBackwardTrigger='<c-z>'
let g:UltiSnipsEditSplit='vertical'
let g:UltiSnipsSnippetDirectories=[$HOME.'/.nvim/plugged/vim-snippets/UltiSnips', $HOME.'/.config/nvim/UltiSnips_custom']

" mappings
source $HOME/.config/nvim/mappings.vim

" misc settings
source $HOME/.config/nvim/misc.vim
