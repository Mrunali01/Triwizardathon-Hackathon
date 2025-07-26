const Header = () => {
  return (
    <header className="py-[1rem] px-[2rem] bg-[#0d0d0d] border-b-[1px] border-solid">
      <div className="max-w-[1200px] flex justify-between items-center">
        <div className="flex items-center gap-[1rem]">
          <div className="relative w-[50px] h-[50px] flex items-center justify-center">
            <div className="w-full h-full absolute">
              <div className="w-full h-full animate-spin ring-1 border-[2px] border-solid border-[#00aaff] absolute border-r-[50%]"></div>
              <div className="w-[80%] h-[80%] absolute animate-spin top-[10%] left-[10%] ring-2 border-[2px] border-solid border-[#00aaff] border-r-[50%]"></div>
              <div className="w-[60%] h-[60%] absolute animate-spin top-[20%] left-[20%] ring-3 border-[2px] border-solid border-[#00aaff] border-r-[50%]"></div>
            </div>
            <div className="bg-gradient-to-r from-[#00aaff] to-[#0066ff] rounded-full w-[30px] h-[30px] flex items-center justify-center font-bold text-[0.8rem] z-[2]">AC</div>
          </div>
          <h1 className="text-[1.5rem] font-bold text-white">
            Smart Web <span className="text-[#00aaff]">Accessibility</span> Checker
          </h1>
        </div>
        <nav className="flex gap-[1rem]">
          <button className="bg-transparent border-[1px] border-solid border-[#000000] text-[#ffffff] py-[0.5rem] px-[1rem] rounded-[8px] transition-all duration-300 ease-in-out hover:text-[#00aaff] cursor-pointer">Features</button>
          <button className="bg-transparent border-[1px] border-solid border-[#000000] text-[#ffffff] py-[0.5rem] px-[1rem] rounded-[8px] transition-all duration-300 ease-in-out hover:text-[#00aaff] cursor-pointer">About</button>
        </nav>
      </div>
    </header>
  );
};

export default Header;
